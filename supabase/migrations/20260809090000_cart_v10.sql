-- GUAMAISON Cart v10
-- Run once in Supabase SQL Editor before using large-cart bulk actions.

begin;

create table if not exists public.cart_checkout_selections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  mode text not null default 'explicit' check (mode in ('explicit', 'all')),
  item_ids uuid[] not null default '{}'::uuid[],
  excluded_ids uuid[] not null default '{}'::uuid[],
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '2 hours')
);

create index if not exists idx_cart_checkout_selection_user_expiry
  on public.cart_checkout_selections (user_id, expires_at desc);

create index if not exists idx_cart_items_user_created_id
  on public.cart_items (user_id, created_at, id);

alter table public.cart_checkout_selections enable row level security;

drop policy if exists cart_checkout_selection_select_own on public.cart_checkout_selections;
create policy cart_checkout_selection_select_own
  on public.cart_checkout_selections for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists cart_checkout_selection_insert_own on public.cart_checkout_selections;
create policy cart_checkout_selection_insert_own
  on public.cart_checkout_selections for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists cart_checkout_selection_delete_own on public.cart_checkout_selections;
create policy cart_checkout_selection_delete_own
  on public.cart_checkout_selections for delete
  to authenticated
  using (auth.uid() = user_id);

grant select, insert, delete on public.cart_checkout_selections to authenticated;
grant all on public.cart_checkout_selections to service_role;

-- The old constraint ignored color/variant.  Normalize the cart around variant_id.
alter table public.cart_items drop constraint if exists unique_cart_item;

with ranked as (
  select
    ci.id,
    ci.variant_id,
    row_number() over (
      partition by ci.user_id, ci.variant_id
      order by ci.created_at, ci.id
    ) as row_number,
    sum(greatest(ci.quantity, 0)) over (
      partition by ci.user_id, ci.variant_id
    ) as merged_quantity
  from public.cart_items ci
  where ci.variant_id is not null
)
update public.cart_items ci
set quantity = least(greatest(r.merged_quantity, 1), greatest(pv.stock, 1)),
    size = pv.size,
    color = pv.color_name
from ranked r
join public.product_variants pv on pv.id = r.variant_id
where ci.id = r.id and r.row_number = 1;

with ranked as (
  select
    ci.id,
    row_number() over (
      partition by ci.user_id, ci.variant_id
      order by ci.created_at, ci.id
    ) as row_number
  from public.cart_items ci
  where ci.variant_id is not null
)
delete from public.cart_items ci
using ranked r
where ci.id = r.id and r.row_number > 1;

create unique index if not exists uq_cart_items_user_variant
  on public.cart_items (user_id, variant_id)
  where variant_id is not null;

create or replace function public.cart_selection_summary_v10(
  p_user_id uuid,
  p_mode text,
  p_item_ids uuid[] default '{}'::uuid[],
  p_excluded_ids uuid[] default '{}'::uuid[]
)
returns jsonb
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select jsonb_build_object(
    'line_count', count(*)::integer,
    'quantity', coalesce(sum(greatest(ci.quantity, 0)), 0)::integer,
    'total', coalesce(sum(
      greatest(ci.quantity, 0) * coalesce(pv.price_override, p.price, 0)
    ), 0)
  )
  from public.cart_items ci
  join public.products p on p.id = ci.product_id
  join public.product_variants pv on pv.id = ci.variant_id
  where ci.user_id = p_user_id
    and p.is_active = true
    and p.deleted_at is null
    and (
      (p_mode = 'explicit' and ci.id = any(coalesce(p_item_ids, '{}'::uuid[])))
      or
      (p_mode = 'all' and not (ci.id = any(coalesce(p_excluded_ids, '{}'::uuid[]))))
    );
$$;

create or replace function public.cart_delete_selection_v10(
  p_user_id uuid,
  p_mode text,
  p_item_ids uuid[] default '{}'::uuid[],
  p_excluded_ids uuid[] default '{}'::uuid[]
)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_affected integer := 0;
begin
  if p_mode not in ('explicit', 'all') then
    raise exception 'invalid cart selection mode';
  end if;

  delete from public.cart_items ci
  where ci.user_id = p_user_id
    and (
      (p_mode = 'explicit' and ci.id = any(coalesce(p_item_ids, '{}'::uuid[])))
      or
      (p_mode = 'all' and not (ci.id = any(coalesce(p_excluded_ids, '{}'::uuid[]))))
    );

  get diagnostics v_affected = row_count;
  return v_affected;
end;
$$;

create or replace function public.cart_change_variant_v10(
  p_user_id uuid,
  p_item_id uuid,
  p_variant_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_current public.cart_items%rowtype;
  v_target public.product_variants%rowtype;
  v_existing public.cart_items%rowtype;
  v_saved public.cart_items%rowtype;
  v_quantity integer;
begin
  select * into v_current
  from public.cart_items
  where id = p_item_id and user_id = p_user_id
  for update;

  if not found then
    return jsonb_build_object('success', false, 'message', 'Sản phẩm không còn trong giỏ.');
  end if;

  select * into v_target
  from public.product_variants
  where id = p_variant_id and product_id = v_current.product_id
  for update;

  if not found then
    return jsonb_build_object('success', false, 'message', 'Phân loại không hợp lệ cho sản phẩm này.');
  end if;

  if v_target.stock <= 0 then
    return jsonb_build_object('success', false, 'message', 'Phân loại bạn chọn đã hết hàng.');
  end if;

  if v_current.variant_id = p_variant_id then
    return jsonb_build_object('success', true, 'affected', 0, 'message', 'Sản phẩm đã dùng phân loại này.');
  end if;

  select * into v_existing
  from public.cart_items
  where user_id = p_user_id
    and variant_id = p_variant_id
    and id <> p_item_id
  limit 1
  for update;

  if found then
    v_quantity := least(v_target.stock, greatest(v_existing.quantity, 0) + greatest(v_current.quantity, 1));
    update public.cart_items
    set quantity = v_quantity,
        size = v_target.size,
        color = v_target.color_name
    where id = v_existing.id
    returning * into v_saved;

    delete from public.cart_items where id = v_current.id and user_id = p_user_id;

    return jsonb_build_object(
      'success', true,
      'affected', 2,
      'message', 'Đã đổi phân loại và gộp với sản phẩm có sẵn.',
      'item', to_jsonb(v_saved)
    );
  end if;

  update public.cart_items
  set variant_id = v_target.id,
      size = v_target.size,
      color = v_target.color_name,
      quantity = least(v_target.stock, greatest(v_current.quantity, 1))
  where id = v_current.id and user_id = p_user_id
  returning * into v_saved;

  return jsonb_build_object(
    'success', true,
    'affected', 1,
    'message', 'Đã cập nhật size và màu.',
    'item', to_jsonb(v_saved)
  );
end;
$$;

revoke all on function public.cart_selection_summary_v10(uuid, text, uuid[], uuid[]) from public, anon, authenticated;
revoke all on function public.cart_delete_selection_v10(uuid, text, uuid[], uuid[]) from public, anon, authenticated;
revoke all on function public.cart_change_variant_v10(uuid, uuid, uuid) from public, anon, authenticated;

grant execute on function public.cart_selection_summary_v10(uuid, text, uuid[], uuid[]) to service_role;
grant execute on function public.cart_delete_selection_v10(uuid, text, uuid[], uuid[]) to service_role;
grant execute on function public.cart_change_variant_v10(uuid, uuid, uuid) to service_role;

delete from public.cart_checkout_selections where expires_at <= now();

commit;
