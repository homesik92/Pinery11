-- Pinery Filing 11 HOA: database setup for Supabase.
-- Paste this whole file into Supabase > SQL Editor and click Run. It is safe to run more than once.
--
-- Privacy model
--   * Residents sign up with email + password, then claim a street address.
--   * A board member approves the claim. Only then can that resident read the
--     charges and payments for that one address. Nobody can read another address.
--   * Board members are listed in board_members (see add-board-members.sql) and can read and edit everything.
--   * Announcements, the lot list and the yearly dues amount are public.

create table if not exists public.lots (
  id text primary key,
  address text not null unique,
  street text not null
);

create table if not exists public.dues_years (
  year int primary key,
  amount numeric(10,2) not null check (amount >= 0),
  due_date date not null,
  late_fee numeric(10,2) not null default 0 check (late_fee >= 0),
  grace_days int not null default 30 check (grace_days >= 0)
);

create table if not exists public.board_members (
  email text primary key
);

create table if not exists public.claims (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text default (auth.jwt() ->> 'email'),
  lot_id text not null references public.lots(id),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now()
);

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  lot_id text not null references public.lots(id),
  year int not null,
  amount numeric(10,2) not null check (amount > 0),
  paid_on date not null default current_date,
  method text not null default 'Check',
  reference text,
  created_at timestamptz not null default now()
);

create table if not exists public.adjustments (
  id uuid primary key default gen_random_uuid(),
  lot_id text not null references public.lots(id),
  year int not null,
  amount numeric(10,2) not null,   -- positive adds to what is owed, negative reduces it
  note text,
  created_at timestamptz not null default now()
);

create table if not exists public.owners (
  lot_id text primary key references public.lots(id),
  name text
);

create table if not exists public.announcements (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null default '',
  posted_on date not null default current_date,
  created_at timestamptz not null default now()
);

create index if not exists payments_lot_year on public.payments(lot_id, year);
create index if not exists adjustments_lot_year on public.adjustments(lot_id, year);

-- Board check. Runs with the function owner's rights so residents cannot read board_members directly.
create or replace function public.is_board() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.board_members
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;
revoke all on function public.is_board() from public, anon;
grant execute on function public.is_board() to authenticated;

-- Lots the signed-in resident may see (approved claims only).
create or replace function public.my_lots() returns setof text
language sql stable security definer set search_path = public as $$
  select lot_id from public.claims where user_id = auth.uid() and status = 'approved';
$$;
revoke all on function public.my_lots() from public, anon;
grant execute on function public.my_lots() to authenticated;

alter table public.lots enable row level security;
alter table public.dues_years enable row level security;
alter table public.board_members enable row level security;
alter table public.claims enable row level security;
alter table public.payments enable row level security;
alter table public.adjustments enable row level security;
alter table public.owners enable row level security;
alter table public.announcements enable row level security;

-- Public reading
drop policy if exists lots_read on public.lots;
create policy lots_read on public.lots for select to anon, authenticated using (true);
drop policy if exists dues_years_read on public.dues_years;
create policy dues_years_read on public.dues_years for select to anon, authenticated using (true);
drop policy if exists announcements_read on public.announcements;
create policy announcements_read on public.announcements for select to anon, authenticated using (true);

-- Board writes to public tables
drop policy if exists dues_years_board on public.dues_years;
create policy dues_years_board on public.dues_years for all to authenticated using (public.is_board()) with check (public.is_board());
drop policy if exists announcements_board on public.announcements;
create policy announcements_board on public.announcements for all to authenticated using (public.is_board()) with check (public.is_board());

-- board_members: no policies, so only the is_board() function can read it.

-- Claims: a resident sees and creates only their own, always as pending. The board sees and decides all.
drop policy if exists claims_read on public.claims;
create policy claims_read on public.claims for select to authenticated using (user_id = auth.uid() or public.is_board());
drop policy if exists claims_insert on public.claims;
create policy claims_insert on public.claims for insert to authenticated
  with check (user_id = auth.uid() and status = 'pending' and email is not distinct from (auth.jwt() ->> 'email'));
drop policy if exists claims_delete_own_pending on public.claims;
create policy claims_delete_own_pending on public.claims for delete to authenticated
  using ((user_id = auth.uid() and status = 'pending') or public.is_board());
drop policy if exists claims_board_update on public.claims;
create policy claims_board_update on public.claims for update to authenticated using (public.is_board()) with check (public.is_board());

-- Money: a resident reads only rows for their own approved address. Only the board writes.
drop policy if exists payments_read on public.payments;
create policy payments_read on public.payments for select to authenticated
  using (public.is_board() or lot_id in (select public.my_lots()));
drop policy if exists payments_board on public.payments;
create policy payments_board on public.payments for all to authenticated using (public.is_board()) with check (public.is_board());

drop policy if exists adjustments_read on public.adjustments;
create policy adjustments_read on public.adjustments for select to authenticated
  using (public.is_board() or lot_id in (select public.my_lots()));
drop policy if exists adjustments_board on public.adjustments;
create policy adjustments_board on public.adjustments for all to authenticated using (public.is_board()) with check (public.is_board());

drop policy if exists owners_board on public.owners;
create policy owners_board on public.owners for all to authenticated using (public.is_board()) with check (public.is_board());

-- Table privileges (RLS above decides which rows).
grant select on public.lots, public.dues_years, public.announcements to anon, authenticated;
grant select, insert, update, delete on public.dues_years, public.announcements, public.payments, public.adjustments, public.owners to authenticated;
grant select, insert, update, delete on public.claims to authenticated;
revoke all on public.board_members from anon, authenticated;
revoke all on public.payments, public.adjustments, public.owners, public.claims from anon;

-- The 45 lots from the Filing 11 address list.
insert into public.lots (id, address, street) values
  ('L001', '6204 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L002', '6205 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L003', '6218 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L004', '6219 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L005', '6232 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L006', '6233 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L007', '6246 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L008', '6247 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L009', '6260 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L010', '6261 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L011', '6275 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L012', '6288 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L013', '6289 Northstar Ridge Ln', 'Northstar Ridge Ln'),
  ('L014', '9009 Northwoods Glen Ct', 'Northwoods Glen Ct'),
  ('L015', '9022 Northwoods Glen Ct', 'Northwoods Glen Ct'),
  ('L016', '9023 Northwoods Glen Ct', 'Northwoods Glen Ct'),
  ('L017', '9037 Northwoods Glen Ct', 'Northwoods Glen Ct'),
  ('L018', '6209 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L019', '6215 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L020', '6221 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L021', '6227 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L022', '6229 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L023', '6233 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L024', '6234 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L025', '6239 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L026', '6241 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L027', '6245 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L028', '6250 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L029', '6251 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L030', '6256 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L031', '6257 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L032', '6264 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L033', '6265 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L034', '6268 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L035', '6269 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L036', '6274 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L037', '6275 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L038', '6280 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L039', '6281 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L040', '6286 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L041', '6287 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L042', '6292 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L043', '6293 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L044', '6298 Northwoods Glen Dr', 'Northwoods Glen Dr'),
  ('L045', '6209 Ponderosa Way', 'Ponderosa Way')
on conflict (id) do nothing;

-- Starting dues year. Sample due date and late fee: the board should check and edit these on the Board page.
insert into public.dues_years (year, amount, due_date, late_fee, grace_days)
values (2026, 30, '2026-11-01', 0, 30)
on conflict (year) do nothing;

-- Board access: add each board member's email here (run separately, and keep the list out of public files):
--   insert into public.board_members (email) values ('person@example.com') on conflict do nothing;
