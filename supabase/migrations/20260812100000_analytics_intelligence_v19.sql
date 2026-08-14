-- GUAMAISON Analytics Intelligence v19.0.0
-- Optional marketplace/export foundation. The core Website/POS report works
-- before this migration. Run in Supabase SQL Editor when enabling connectors.

create extension if not exists pgcrypto;

create or replace function public.gua_set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.marketplace_connections (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (provider in ('shopee', 'lazada', 'tiktok_shop')),
  shop_id text not null,
  shop_name text,
  status text not null default 'pending' check (status in ('pending', 'active', 'expired', 'revoked', 'error', 'disabled')),
  scopes jsonb not null default '[]'::jsonb,
  token_ciphertext text,
  refresh_token_ciphertext text,
  token_expires_at timestamptz,
  last_synced_at timestamptz,
  last_error text,
  created_by uuid references public.users(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (provider, shop_id)
);

create table if not exists public.marketplace_sync_runs (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null references public.marketplace_connections(id) on delete cascade,
  sync_type text not null default 'incremental' check (sync_type in ('initial', 'incremental', 'reconcile', 'webhook')),
  status text not null default 'running' check (status in ('running', 'success', 'partial', 'failed')),
  cursor_value text,
  rows_received integer not null default 0 check (rows_received >= 0),
  rows_upserted integer not null default 0 check (rows_upserted >= 0),
  error_summary text,
  started_at timestamptz not null default timezone('utc', now()),
  finished_at timestamptz,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.external_orders (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (provider in ('shopee', 'lazada', 'tiktok_shop')),
  shop_id text not null,
  external_order_id text not null,
  sales_channel text not null,
  order_status text,
  payment_status text,
  currency text not null default 'VND',
  gross_amount numeric(16, 2) not null default 0,
  discount_amount numeric(16, 2) not null default 0,
  refund_amount numeric(16, 2) not null default 0,
  marketplace_fee numeric(16, 2) not null default 0,
  shipping_fee numeric(16, 2) not null default 0,
  net_amount numeric(16, 2) not null default 0,
  ordered_at timestamptz,
  completed_at timestamptz,
  source_updated_at timestamptz,
  raw_checksum text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (provider, shop_id, external_order_id)
);

create table if not exists public.external_order_items (
  id uuid primary key default gen_random_uuid(),
  external_order_pk uuid not null references public.external_orders(id) on delete cascade,
  external_line_item_id text not null,
  external_product_id text,
  external_sku_id text,
  seller_sku text,
  product_name text,
  variant_name text,
  quantity integer not null default 0 check (quantity >= 0),
  returned_quantity integer not null default 0 check (returned_quantity >= 0),
  unit_price numeric(16, 2) not null default 0,
  item_discount numeric(16, 2) not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (external_order_pk, external_line_item_id)
);

create table if not exists public.product_channel_mappings (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  variant_id uuid references public.product_variants(id) on delete cascade,
  provider text not null check (provider in ('shopee', 'lazada', 'tiktok_shop')),
  shop_id text not null,
  external_product_id text not null,
  external_sku_id text,
  seller_sku text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (provider, shop_id, external_product_id, external_sku_id)
);

create table if not exists public.report_export_templates (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id uuid references public.users(id) on delete cascade,
  report_type text not null default 'analytics_intelligence',
  configuration jsonb not null default '{}'::jsonb,
  is_default boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_marketplace_sync_runs_connection_started
  on public.marketplace_sync_runs (connection_id, started_at desc);
create index if not exists idx_external_orders_provider_ordered
  on public.external_orders (provider, shop_id, ordered_at desc);
create index if not exists idx_external_orders_status
  on public.external_orders (order_status, payment_status);
create index if not exists idx_external_order_items_product
  on public.external_order_items (external_product_id, external_sku_id);
create index if not exists idx_product_channel_mappings_product
  on public.product_channel_mappings (product_id, variant_id);
create index if not exists idx_report_export_templates_owner
  on public.report_export_templates (owner_id, report_type);

drop trigger if exists trg_marketplace_connections_updated_at on public.marketplace_connections;
create trigger trg_marketplace_connections_updated_at
before update on public.marketplace_connections
for each row execute function public.gua_set_updated_at();

drop trigger if exists trg_external_orders_updated_at on public.external_orders;
create trigger trg_external_orders_updated_at
before update on public.external_orders
for each row execute function public.gua_set_updated_at();

drop trigger if exists trg_external_order_items_updated_at on public.external_order_items;
create trigger trg_external_order_items_updated_at
before update on public.external_order_items
for each row execute function public.gua_set_updated_at();

drop trigger if exists trg_product_channel_mappings_updated_at on public.product_channel_mappings;
create trigger trg_product_channel_mappings_updated_at
before update on public.product_channel_mappings
for each row execute function public.gua_set_updated_at();

drop trigger if exists trg_report_export_templates_updated_at on public.report_export_templates;
create trigger trg_report_export_templates_updated_at
before update on public.report_export_templates
for each row execute function public.gua_set_updated_at();

alter table public.marketplace_connections enable row level security;
alter table public.marketplace_sync_runs enable row level security;
alter table public.external_orders enable row level security;
alter table public.external_order_items enable row level security;
alter table public.product_channel_mappings enable row level security;
alter table public.report_export_templates enable row level security;

-- No client policies are created intentionally. These tables contain internal
-- reporting metadata and encrypted credentials; server-side service_role is
-- the only supported access path until explicit admin policies are designed.
revoke all on public.marketplace_connections from anon, authenticated;
revoke all on public.marketplace_sync_runs from anon, authenticated;
revoke all on public.external_orders from anon, authenticated;
revoke all on public.external_order_items from anon, authenticated;
revoke all on public.product_channel_mappings from anon, authenticated;
revoke all on public.report_export_templates from anon, authenticated;

comment on column public.marketplace_connections.token_ciphertext is
  'Encrypted access token only. Never store a plaintext marketplace token.';
comment on table public.external_orders is
  'Normalized marketplace facts without customer PII; upsert by provider/shop/order.';

