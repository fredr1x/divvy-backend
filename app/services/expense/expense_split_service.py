from decimal import ROUND_HALF_UP, Decimal
from itertools import chain

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ExpenseSplit, GroupExpense, UserGroup, User, AuditLog
from app.models.enums import ShareType, SplitStatus, SplitType, ActionType, ActionStatus
from app.schemas import ItemCreate, ItemUpdate, UserRead
from app.schemas.expense_split import (
    AllExpensesByGroupAndUser,
    OwedAmountDetail,
    ReceivableAmountDetail, ExpenseSplitDetails,
)
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseUpdate
from app.services.user.user_group_service import get_group_members
from app.services.audit.audit_logs_service import create_failed_audit_log


async def get_expense_split_by_id(
    ip_address: str,
    db: AsyncSession,
    current_user: User,
    expense_split_id: int
) -> ExpenseSplit:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="EXPENSE_SPLIT",
    )

    expense_split: ExpenseSplit = await db.scalar(
        select(ExpenseSplit).where(ExpenseSplit.id == expense_split_id)
    )

    if not expense_split:
        message="Expense split not found"
        await create_failed_audit_log(db, audit_log, message)

        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id=expense_split.id
    audit_log.message="Successfully retrieved expense split"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    return expense_split


async def get_all_expenses_by_group_id_and_user_id(
    ip_address: str,
    db: AsyncSession,
    group_id: int,
    user_id: int,
) -> AllExpensesByGroupAndUser:
    validate = select(UserGroup).where(
        UserGroup.group_id == group_id, UserGroup.user_id == user_id
    )

    audit_log: AuditLog = AuditLog(
        user_id=user_id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="EXPENSE_SPLIT",
    )

    user_group = await db.scalar(validate)
    if not user_group:
        message=f"User is not a member of the group {group_id}"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=403, detail=message)

    find_all_group_expenses = (
        select(GroupExpense)
        .options(selectinload(GroupExpense.splits))
        .where(GroupExpense.group_id == group_id)
    )
    group_expenses = (await db.scalars(find_all_group_expenses)).all()

    owed_amount_details: list[OwedAmountDetail] = []
    receivable_amount_details: list[ReceivableAmountDetail] = []
    total_owed = Decimal("0")
    total_receivable = Decimal("0")

    for expense in group_expenses:
        for split in expense.splits:
            if split.user_id == user_id and expense.payer_id != user_id:
                owed_amount_details.append(
                    OwedAmountDetail(
                        to_user_id=expense.payer_id, amount=split.owed_amount
                    )
                )
                total_owed += split.owed_amount

            elif expense.payer_id == user_id and split.user_id != user_id:
                receivable_amount_details.append(
                    ReceivableAmountDetail(
                        from_user_id=split.user_id, amount=abs(split.owed_amount)
                    )
                )
                total_receivable += abs(split.owed_amount)

    audit_log.message="Successfully retrieved expense split details"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    return AllExpensesByGroupAndUser(
        group_id=group_id,
        user_id=user_id,
        total_owed_amount=total_owed,
        total_receivable_amount=total_receivable,
        owed_amount_details=owed_amount_details,
        receivable_amount_details=receivable_amount_details,
    )


async def create_expense_split(
    ip_address: str,
    db: AsyncSession,
    payload: GroupExpenseCreate,
    group_expense: GroupExpense,
    current_user: User,
) -> None:
    group_members = await get_group_members(db, payload.group_id)

    owed_map = build_owed_amount_map(
        group_members=group_members,
        payer_id=payload.payer_id,
        total_amount=payload.total_amount,
        share_type=payload.share_type,
        expense_members=payload.expense_members,
        expense_items=payload.expense_items,
        exact_share_amount=payload.exact_share_amount,
        percentage_share_amount=payload.percentage_share_amount,
    )

    await persist_snapshot_splits(ip_address,
                                  db,
                                  group_expense.id,
                                  payload.payer_id,
                                  owed_map,
                                  current_user.id,
                                  ActionType.CREATE,
                                  )


async def update_expense_split(
    ip_address: str,
    db: AsyncSession,
    group_expense: GroupExpense,
    payload: GroupExpenseUpdate,
    current_user_id: int,
) -> None:
    group_members: list[UserRead] = await get_group_members(db, group_expense.group_id)
    total_amount = normalize_amount(payload.total_amount)

    if total_amount <= 0:
        raise HTTPException(
            status_code=400, detail="Total amount must be greater than zero"
        )

    expense_splits = list(
        (await db.scalars(
            select(ExpenseSplit).where(
                ExpenseSplit.group_expense_id == group_expense.id
            )
        )).all()
    )

    if expense_splits and all(
        split.status == SplitStatus.PAID for split in expense_splits
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot recalculate splits for a fully settled expense",
        )

    owed_map = build_owed_amount_map(
        group_members=group_members,
        payer_id=group_expense.payer_id,
        total_amount=total_amount,
        share_type=payload.share_type,
        expense_members=payload.expense_members,
        expense_items=payload.expense_items,
        exact_share_amount=payload.exact_share_amount,
        percentage_share_amount=payload.percentage_share_amount,
    )

    await persist_snapshot_splits(
        ip_address,
        db,
        group_expense.id,
        group_expense.payer_id,
        owed_map,
        current_user_id,
        ActionType.UPDATE,
        expense_splits,
    )


def build_owed_amount_map(
    group_members: list[UserRead],
    payer_id: int,
    total_amount: Decimal,
    share_type: ShareType,
    expense_members: list[int],
    expense_items: list[ItemCreate | ItemUpdate] | None,
    exact_share_amount: dict[int, Decimal] | None,
    percentage_share_amount: dict[int, Decimal] | None,
) -> dict[int, Decimal]:
    validate_group_members(group_members, expense_members)
    if payer_id not in set(expense_members):
        raise HTTPException(
            status_code=400, detail="Payer must be included in expense members"
        )

    normalized_total = normalize_amount(total_amount)
    if normalized_total <= 0:
        raise HTTPException(
            status_code=400, detail="Total amount must be greater than zero"
        )

    shares = calculate_member_shares(
        share_type=share_type,
        total_amount=normalized_total,
        expense_members=expense_members,
        payer_id=payer_id,
        expense_items=expense_items,
        exact_share_amount=exact_share_amount,
        percentage_share_amount=percentage_share_amount,
        group_members=group_members,
    )

    total_shares = sum(shares.values(), Decimal("0.00"))
    if abs(total_shares - normalized_total) > Decimal("0.01"):
        raise HTTPException(
            status_code=400, detail="Calculated shares must sum to total amount"
        )

    owed_map: dict[int, Decimal] = {}
    for user_id in expense_members:
        share = shares[user_id]
        owed_map[user_id] = share if user_id == payer_id else -share
    return owed_map


def calculate_member_shares(
    share_type: ShareType,
    total_amount: Decimal,
    expense_members: list[int],
    payer_id: int,
    expense_items: list[ItemCreate | ItemUpdate] | None,
    exact_share_amount: dict[int, Decimal] | None,
    percentage_share_amount: dict[int, Decimal] | None,
    group_members: list[UserRead],
) -> dict[int, Decimal]:
    if share_type == ShareType.EQUAL:
        count = len(expense_members)
        each = normalize_amount(total_amount / count)
        remainder = total_amount - (each * count)
        shares = {user_id: each for user_id in expense_members}
        shares[payer_id] = normalize_amount(shares[payer_id] + remainder)
        return shares

    if share_type == ShareType.ITEMIZED:
        if not expense_items:
            raise HTTPException(
                status_code=400, detail="Expense items must be provided"
            )

        validate_expense_items(group_members, expense_items, expense_members)
        shares = {user_id: Decimal("0.00") for user_id in expense_members}

        for item in expense_items:
            count = len(item.assigned_user_ids)
            each = normalize_amount(item.total_price / count)
            remainder = item.total_price - (each * count)

            for idx, user_id in enumerate(item.assigned_user_ids):
                amount = each + remainder if idx == 0 else each
                shares[user_id] = normalize_amount(shares[user_id] + amount)

        return shares

    if share_type == ShareType.EXACT:
        if not exact_share_amount:
            raise HTTPException(status_code=400, detail="Exact shares are required")

        validate_shares(exact_share_amount, "exact")
        normalized = {
            int(k): normalize_amount(v) for k, v in exact_share_amount.items()
        }
        if set(normalized.keys()) != set(expense_members):
            raise HTTPException(
                status_code=400, detail="Exact shares must match expense members"
            )

        return normalized

    if share_type == ShareType.PERCENTAGE:
        if not percentage_share_amount:
            raise HTTPException(
                status_code=400, detail="Percentage shares are required"
            )

        validate_shares(percentage_share_amount, "percentage")
        normalized = {
            int(k): normalize_amount(v) for k, v in percentage_share_amount.items()
        }
        if set(normalized.keys()) != set(expense_members):
            raise HTTPException(
                status_code=400, detail="Percentage shares must match expense members"
            )

        total_percentage = sum(normalized.values(), Decimal("0.00"))
        if total_percentage != Decimal("100.00"):
            raise HTTPException(
                status_code=400, detail="Percentage shares must sum to 100"
            )

        shares = {
            user_id: normalize_amount(total_amount * pct / Decimal("100.00"))
            for user_id, pct in normalized.items()
        }
        remainder = total_amount - sum(shares.values(), Decimal("0.00"))
        shares[payer_id] = normalize_amount(shares[payer_id] + remainder)
        return shares

    raise HTTPException(status_code=400, detail="Unsupported share type")


async def persist_snapshot_splits(
    ip_address: str,
    db: AsyncSession,
    group_expense_id: int,
    payer_id: int,
    owed_map: dict[int, Decimal],
    current_user_id: int,
    action_type: ActionType,
    existing_splits: list[ExpenseSplit] | None = None,
) -> None:

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=action_type,
        ip_address=ip_address,
        entity_name="EXPENSE_SPLIT",
    )

    if existing_splits is None:
        existing_splits = list(
            (await db.scalars(
                select(ExpenseSplit).where(
                    ExpenseSplit.group_expense_id == group_expense_id
                )
            )).all()
        )

    old_values_list = []
    for split in existing_splits:
        old_values_list.append(ExpenseSplitDetails.model_validate(split).model_dump(mode="json"))
        await db.delete(split)

    audit_log.old_values=old_values_list

    new_values_list = []
    for user_id, owed_amount in owed_map.items():
        expense_split = build_expense(user_id,
                                      group_expense_id,
                                      owed_amount,
                                      SplitType.ORIGINAL,
                                      user_id == payer_id,
                                      )
        db.add(expense_split)
        await db.flush()
        new_values_list.append(ExpenseSplitDetails.model_validate(expense_split).model_dump(mode="json"))

    audit_log.new_values=new_values_list

    audit_log.message=f"Successfully {action_type.name.lower()}d expense splits of group_expense {group_expense_id}"
    audit_log.action_status=ActionStatus.SUCCESS
    db.add(audit_log)
    await db.commit()


def build_expense(
    member_id: int,
    group_expense_id: int,
    amount_for_each_member: Decimal,
    split_type: SplitType,
    payer: bool,
    refund_to_user_id: int | None = None,
) -> ExpenseSplit:
    return ExpenseSplit(
        user_id=member_id,
        group_expense_id=group_expense_id,
        owed_amount=amount_for_each_member,
        status=SplitStatus.PAID if payer else SplitStatus.PENDING,
        split_type=split_type,
        refund_to_user_id=refund_to_user_id,
    )



def normalize_amount(value: Decimal | int | float) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_shares(
    share_map: dict[int, Decimal] | None,
    share_type: str,
) -> dict[int, Decimal]:
    if not share_map:
        raise HTTPException(
            status_code=400, detail=f"{share_type.capitalize()} shares are required"
        )

    validated: dict[int, Decimal] = {}
    for member_id, amount in share_map.items():
        try:
            user_id = int(member_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400, detail="Share map keys must be user ids"
            ) from None

        normalized_amount = normalize_amount(amount)
        if normalized_amount < 0:
            raise HTTPException(status_code=400, detail="Shares must be non-negative")
        validated[user_id] = normalized_amount

    return validated


def validate_group_members(
    group_members: list[UserRead],
    expense_members: list[int],
    shares: dict[int, Decimal] | None = None,
) -> None:
    group_member_ids = {member.id for member in group_members}
    expense_ids = set(expense_members)

    unknown_members = expense_ids - group_member_ids
    if unknown_members:
        raise HTTPException(
            status_code=400, detail="Expense members includes unknown members"
        )

    if shares is None:
        return

    share_ids = set(shares.keys())
    unknown_members = share_ids - group_member_ids
    if unknown_members:
        raise HTTPException(status_code=400, detail="Share includes unknown members")


def validate_expense_items(
    group_members: list[UserRead],
    expense_items: list[ItemCreate | ItemUpdate],
    expense_members: list[int],
) -> None:
    for idx, item in enumerate(expense_items, start=1):
        if not item.assigned_user_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Item #{idx} must have at least one assigned user",
            )

        assigned_ids = item.assigned_user_ids
        if len(assigned_ids) != len(set(assigned_ids)):
            raise HTTPException(
                status_code=400, detail=f"Item #{idx} has duplicate assigned users"
            )

    group_member_ids = {member.id for member in group_members}
    all_assigned_user_ids = set(
        chain.from_iterable(item.assigned_user_ids for item in expense_items)
    )

    unknown_user_ids = all_assigned_user_ids - group_member_ids
    if unknown_user_ids:
        raise HTTPException(
            status_code=400, detail="Expense items include unknown users"
        )

    invalid_users = all_assigned_user_ids - set(expense_members)
    if invalid_users:
        raise HTTPException(
            status_code=400,
            detail=f"Users {invalid_users} are assigned to items but not in expense members",
        )

    unassigned_users = set(expense_members) - all_assigned_user_ids
    if unassigned_users:
        raise HTTPException(
            status_code=400,
            detail=f"Users {unassigned_users} are expense members but not assigned to any item",
        )
