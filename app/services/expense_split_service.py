from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, ExpenseSplit
from app.models.enums import ShareType
from app.schemas.group_expense import GroupExpenseCreate
from app.services.user_group_service import get_group_members


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


def validate_create_expense_request(group_members: list[User], payload: GroupExpenseCreate):
    if not group_members:
        raise HTTPException(status_code=404, detail="Group members not found")

    member_ids = {member.id for member in group_members}
    if payload.payer_id not in member_ids:
        raise HTTPException(status_code=400, detail="Payer is not a member of this group")


def calculate_and_save_equal_share_type(db: Session,
                                        group_expense_id: int,
                                        group_members: list[User],
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
                         ShareType.EQUAL)

        else:
            build_expense(
                db,
                member.id,
                group_expense_id,
                -abs(amount_for_each_member),
                ShareType.EQUAL
            )


def calculate_and_save_exact_share_type(db: Session,
                                        group_expense_id: int,
                                        group_members: list[User],
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
        else:
            owed_amount = -share
        build_expense(db, member.id, group_expense_id, owed_amount, ShareType.EXACT)


def calculate_and_save_percentage_share_type(db: Session,
                                             group_expense_id: int,
                                             group_members: list[User],
                                             payload: GroupExpenseCreate):
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
        else:
            owed_amount = -share
        build_expense(db, member.id, group_expense_id, owed_amount, ShareType.PERCENTAGE)


def build_expense(db: Session,
                  member_id: int,
                  group_expense_id: int,
                  amount_for_each_member: Decimal,
                  share_type: ShareType) -> None:
    split = ExpenseSplit(user_id=member_id,
                         group_expense_id=group_expense_id,
                         owed_amount=amount_for_each_member,
                         share_type=share_type)

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
    group_members: list[User],
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
