from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ExpenseSplit, GroupExpense, UserGroup
from app.models.enums import ShareType, SplitStatus
from app.schemas import UserRead
from app.schemas.expense_split import AllExpensesByGroupAndUser, OwedAmountDetail, ReceivableAmountDetail
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseUpdate
from app.services.user_group_service import get_group_members


def get_all_expenses_by_group_id_and_user_id(
        db: Session,
        group_id: int,
        user_id: int
)-> AllExpensesByGroupAndUser:
    validate = (
        select(UserGroup)
        .where(
            UserGroup.group_id == group_id,
            UserGroup.user_id == user_id
        )
    )

    user_group = db.scalar(validate)

    if not user_group:
        raise HTTPException(status_code=403, detail="User is not a member of this group")

    find_all_group_expenses = (select(GroupExpense)
                               .options(selectinload(GroupExpense.splits))
                               .where(GroupExpense.group_id == group_id))

    group_expenses = db.scalars(find_all_group_expenses).all()

    owed_amount_details: list[OwedAmountDetail] = []
    receivable_amount_details: list[ReceivableAmountDetail] = []
    total_owed = Decimal("0")
    total_receivable = Decimal("0")

    for expense in group_expenses:
        for split in expense.splits:
            if split.user_id == user_id and expense.payer_id != user_id:
                owed_amount_details.append(
                    OwedAmountDetail(
                        to_user_id=expense.payer_id,
                        amount=split.owed_amount
                    )
                )
                total_owed += split.owed_amount

            elif expense.payer_id == user_id and split.user_id != user_id:
                receivable_amount_details.append(
                    ReceivableAmountDetail(
                        from_user_id=split.user_id,
                        amount=abs(split.owed_amount)
                    )
                )
                total_receivable += abs(split.owed_amount)

    result = AllExpensesByGroupAndUser(group_id=group_id,
                                       user_id=user_id,
                                       total_owed_amount=total_owed,
                                       total_receivable_amount=total_receivable,
                                       owed_amount_details=owed_amount_details,
                                       receivable_amount_details=receivable_amount_details)
    return result

def create_expense_split(
    db: Session,
    payload: GroupExpenseCreate,
    group_expense_id: int
) -> None:
    group_members = get_group_members(payload.group_id, db)
    validate_create_expense_request(group_members, payload)

    share_type = payload.share_type
    if share_type == ShareType.EQUAL:
        calculate_and_save_equal_share_type(db, group_expense_id, group_members, payload)

    elif share_type == ShareType.EXACT:
        calculate_and_save_exact_share_type(db, group_expense_id, group_members, payload)

    elif share_type == ShareType.PERCENTAGE:
        calculate_and_save_percentage_share_type(db, group_expense_id, group_members, payload)
    else:
        raise HTTPException(status_code=400, detail="Unsupported share type")


def update_expense_split(
        db: Session,
        group_expense: GroupExpense,
        payload: GroupExpenseUpdate
)-> None:
    group_members = get_group_members(group_expense.group_id, db)
    total_amount = normalize_amount(payload.total_amount)

    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="Total amount must be greater than zero")

    payer_id = group_expense.payer_id
    share_type = payload.share_type

    if share_type == ShareType.EQUAL:
        calculate_and_update_equal_share_type(db, group_expense.id, payer_id, total_amount, group_members)

    elif share_type == ShareType.EXACT:
        calculate_and_update_exact_share_type(db, group_expense.id, payer_id, total_amount, payload.exact_share_amount, group_members)

    elif share_type == ShareType.PERCENTAGE:
        calculate_and_update_percentage_share_type(db, group_expense.id, payer_id, total_amount, payload.percentage_share_amount, group_members)

    else:
        raise HTTPException(status_code=400, detail="Unsupported share type")

def validate_create_expense_request(group_members: list[UserRead], payload: GroupExpenseCreate):
    if not group_members:
        raise HTTPException(status_code=404, detail="Group members not found")

    member_ids = {member.id for member in group_members}
    if payload.payer_id not in member_ids:
        raise HTTPException(status_code=400, detail="Payer is not a member of this group")


def calculate_and_save_equal_share_type(db: Session,
                                        group_expense_id: int,
                                        group_members: list[UserRead],
                                        payload: GroupExpenseCreate):

    total_amount = normalize_amount(payload.total_amount)

    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="Total amount must be greater than zero")

    amount_for_each_member = normalize_amount(total_amount / len(group_members))
    remainder = total_amount - (amount_for_each_member * len(group_members))
    payer_share = amount_for_each_member + remainder
    for member in group_members:
        if member.id == payload.payer_id:
            build_expense(db,
                         member.id,
                         group_expense_id,
                         total_amount - payer_share,
                         ShareType.EQUAL,
                          True
            )

        else:
            build_expense(
                db,
                member.id,
                group_expense_id,
                -abs(amount_for_each_member),
                ShareType.EQUAL,
                False
            )


def calculate_and_save_exact_share_type(db: Session,
                                        group_expense_id: int,
                                        group_members: list[UserRead],
                                        payload: GroupExpenseCreate):
    total_amount = normalize_amount(payload.total_amount)
    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="Total amount must be greater than zero")

    shares = validate_shares(payload.exact_share_amount, "exact")
    validate_group_members(group_members, shares, "exact")

    total_shares = sum(shares.values(), Decimal("0.00"))
    if total_shares != total_amount:
        raise HTTPException(status_code=400, detail="Exact shares must sum to total amount")

    for member in group_members:
        share = shares[member.id]
        if member.id == payload.payer_id:
            owed_amount = total_amount - share
            build_expense(db,
                          member.id,
                          group_expense_id,
                          owed_amount,
                          ShareType.EXACT,
                          True
            )

        else:
            owed_amount = -share
        build_expense(db,
                      member.id,
                      group_expense_id,
                      owed_amount,
                      ShareType.EXACT,
                      False
        )


def calculate_and_save_percentage_share_type(db: Session,
                                             group_expense_id: int,
                                             group_members: list[UserRead],
                                             payload: GroupExpenseCreate
):
    total_amount = normalize_amount(payload.total_amount)
    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="Total amount must be greater than zero")

    percentages = validate_percentages(payload.percentage_share_amount)
    validate_group_members(group_members, percentages, "percentage")

    total_percentage = sum(percentages.values(), Decimal("0.00"))
    if total_percentage !=  Decimal("100.00"):
        raise HTTPException(status_code=400, detail="Percentage shares must sum to 100")

    shares: dict[int, Decimal] = {}
    for member in group_members:
        percent = percentages[member.id]
        shares[member.id] = normalize_amount(total_amount * percent / Decimal("100.00"))

    remainder = total_amount - sum(shares.values(), Decimal("0.00"))
    shares[payload.payer_id] = normalize_amount(shares[payload.payer_id] + remainder)

    for member in group_members:
        share = shares[member.id]
        if member.id == payload.payer_id:
            owed_amount = total_amount - share
            build_expense(db,
                          member.id,
                          group_expense_id,
                          owed_amount,
                          ShareType.PERCENTAGE,
                          True
            )
        else:
            owed_amount = -share
        build_expense(db,
                      member.id,
                      group_expense_id,
                      owed_amount,
                      ShareType.PERCENTAGE,
                      False
        )


def build_expense(db: Session,
                  member_id: int,
                  group_expense_id: int,
                  amount_for_each_member: Decimal,
                  share_type: ShareType,
                  payer: bool,
) -> None:

    split = ExpenseSplit(user_id=member_id,
                         group_expense_id=group_expense_id,
                         owed_amount=amount_for_each_member,
                         share_type=share_type,
                         split_status=SplitStatus.PAYER if payer else SplitStatus.PENDING
    )

    db.add(split)


def normalize_amount(value: Decimal | int | float) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_shares(
    share_map: dict[int, Decimal] | None,
    share_type: str,
) -> dict[int, Decimal]:
    if not share_map:
        raise HTTPException(status_code=400, detail=f"{share_type.capitalize()} shares are required")

    validated: dict[int, Decimal] = {}
    for member_id, amount in share_map.items():
        try:
            user_id = int(member_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Share map keys must be user ids") from None

        normalized_amount = normalize_amount(amount)
        if normalized_amount < 0:
            raise HTTPException(status_code=400, detail="Shares must be non-negative")
        validated[user_id] = normalized_amount

    return validated


def validate_percentages(
    share_map: dict[int, Decimal] | None,
) -> dict[int, Decimal]:
    percentages = validate_shares(share_map, "percentage")
    for value in percentages.values():
        if value > Decimal("100.00"):
            raise HTTPException(status_code=400, detail="Percentages must be between 0 and 100")
    return percentages


def validate_group_members(
    group_members: list[UserRead],
    shares: dict[int, Decimal],
    share_type: str,
) -> None:
    member_ids = {member.id for member in group_members}
    share_ids = set(shares.keys())

    unknown_members = share_ids - member_ids
    if unknown_members:
        raise HTTPException(status_code=400, detail=f"{share_type.capitalize()} shares include unknown users")

    # set subtract
    missing_members = member_ids - share_ids
    if missing_members:
        raise HTTPException(status_code=400, detail=f"{share_type.capitalize()} shares must include all group members")


def calculate_and_update_equal_share_type(db: Session,
                                          group_expense_id: int,
                                          payer_id: int,
                                          total_amount: Decimal,
                                          group_members: list[UserRead],
):
    find_expense_splits = select(ExpenseSplit).where(ExpenseSplit.group_expense_id == group_expense_id)

    expense_splits = db.scalars(find_expense_splits).all()

    amount_for_each_member = normalize_amount(total_amount / len(group_members))
    remainder = total_amount - (amount_for_each_member * len(group_members))
    payer_share = amount_for_each_member + remainder

    now = datetime.now()
    for split in expense_splits:
        if split.user_id == payer_id:
            split.owed_amount = payer_share
        else:
            split.owed_amount = -abs(payer_share)
        split.last_modified_at = now
        split.share_type = ShareType.EQUAL

    db.commit()


def calculate_and_update_exact_share_type(db: Session,
                                          group_expense_id: int,
                                          payer_id: int,
                                          total_amount: Decimal,
                                          exact_share_amount: dict[int, Decimal],
                                          group_members: list[UserRead]
):
    shares = validate_shares(exact_share_amount, "exact")
    validate_group_members(group_members, shares, "exact")

    total_shares = sum(shares.values(), Decimal("0.00"))
    if total_shares != total_amount:
        raise HTTPException(status_code=400, detail="Exact shares must sum to total amount")

    find_expense_splits = select(ExpenseSplit).where(ExpenseSplit.group_expense_id == group_expense_id)

    expense_splits = db.scalars(find_expense_splits).all()
    now = datetime.now()

    for split in expense_splits:
        share = shares[split.user_id]
        if split.user_id == payer_id:
            split.owed_amount = total_amount - share
        else:
            split.owed_amount = -abs(share)
        split.last_modified_at = now
        split.share_type = ShareType.EXACT

    db.commit()


def calculate_and_update_percentage_share_type(db: Session,
                                               group_expense_id: int,
                                               payer_id: int, total_amount: Decimal,
                                               percentage_share_amount: dict[int, Decimal],
                                               group_members: list[UserRead]
):
    percentages = validate_percentages(percentage_share_amount)
    validate_group_members(group_members, percentages, "percentage")

    total_percentage = sum(percentages.values(), Decimal("0.00"))
    if total_percentage != Decimal("100.00"):
        raise HTTPException(status_code=400, detail="Percentage shares must sum to 100")

    shares: dict[int, Decimal] = {}
    for member in group_members:
        percent = percentages[member.id]
        shares[member.id] = normalize_amount(total_amount * percent / Decimal("100.00"))

    remainder = total_amount - sum(shares.values(), Decimal("0.00"))
    shares[payer_id] = normalize_amount(shares[payer_id] + remainder)

    find_expense_splits = select(ExpenseSplit).where(ExpenseSplit.group_expense_id == group_expense_id)

    expense_splits = db.scalars(find_expense_splits).all()
    now = datetime.now()

    for split in expense_splits:
        share = shares[split.user_id]
        if split.user_id == payer_id:
            split.owed_amount = total_amount - share
        else:
            split.owed_amount = -abs(share)
        split.last_modified_at = now
        split.share_type = ShareType.PERCENTAGE

    db.commit()
