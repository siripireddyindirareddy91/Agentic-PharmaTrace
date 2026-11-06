-- Current executable repository. Apply on a dedicated PostgreSQL database.
create table if not exists public.users(id varchar primary key,email varchar not null unique,password varchar not null,name varchar not null,role varchar not null default 'Pharmacist',org varchar not null);
create table if not exists public.records(id varchar primary key,kind varchar not null,org varchar not null,data json not null,created_at varchar not null);
create index if not exists ix_records_kind on public.records(kind);
create index if not exists ix_records_org on public.records(org);
create index if not exists ix_users_email on public.users(email);
-- Deny direct browser access. Backend connects with its dedicated database role.
alter table public.users enable row level security;
alter table public.records enable row level security;
revoke all on public.users,public.records from anon,authenticated;
