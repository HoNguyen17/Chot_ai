-- Chốt — schema M3 (SPEC M3 §5.2). Chạy SAU 001_init.sql; chạy lại nhiều lần vẫn an toàn.
-- Supabase: dán cả file vào SQL editor → Run.

-- Nhóm họp: id = chuỗi ngẫu nhiên ≥ 16 ký tự (link bí mật); read_only = nhóm mẫu chỉ xem.
alter table meeting_series add column if not exists read_only boolean not null default false;

-- id cuộc họp gốc trong transcript ("m01") — cần để replay; meetings.id là id ngẫu nhiên.
alter table meetings add column if not exists source_id text;

-- Bản đồ chủ đề (lượt 1 của extractor) = ledger.threads, lưu để replay.
create table if not exists topic_maps (
  meeting_id  text primary key references meetings(id) on delete cascade,
  threads     jsonb not null default '[]'
);

alter table events add column if not exists durable_hint boolean not null default false;
alter table events add column if not exists new_key      boolean not null default false;
-- LLM có thể gán mã câu không có trong transcript; vẫn lưu nguyên để replay (grounding loại sau).
alter table events drop constraint if exists events_meeting_id_utt_id_fkey;

alter table items add column if not exists reasons      jsonb not null default '[]';
alter table items add column if not exists review_state text check (review_state in (
  'auto_accepted','pending','confirmed','rejected','deferred'));
alter table items add column if not exists scope        text check (scope in ('meeting','durable'));
alter table items add column if not exists timeline     jsonb not null default '[]';
-- Giữ thứ tự mục / người như trong ledger; real (float32) làm lệch confidence khi đọc lại.
alter table items add column if not exists idx int;
alter table participants add column if not exists idx int;
alter table items alter column confidence type double precision;
-- Bằng chứng gồm cả câu trả lời của người duyệt (không có utt) → jsonb trên items.
-- Bảng `evidence` của 001 không dùng từ M3.
alter table items add column if not exists evidence     jsonb not null default '[]';
alter table items drop constraint if exists items_status_check;
alter table items add constraint items_status_check check (status in (
  'final','needs_confirmation','superseded','rejected','deferred','open','noted'));

-- Nhật ký duyệt: append-only. entry_id do app sinh → lưu lại record không chèn trùng.
alter table review_actions add column if not exists action   text check (action in ('confirm','reject','defer'));
alter table review_actions add column if not exists entry_id text unique;

create or replace function review_actions_append_only() returns trigger
language plpgsql as $$
begin
  raise exception 'review_actions chỉ được thêm, không sửa / xoá';
end $$;

drop trigger if exists review_actions_no_update on review_actions;
create trigger review_actions_no_update before update or delete on review_actions
  for each row execute function review_actions_append_only();
drop trigger if exists review_actions_no_truncate on review_actions;
create trigger review_actions_no_truncate before truncate on review_actions
  for each statement execute function review_actions_append_only();

-- Kho tri thức của nhóm họp: chỉ tri thức lâu dài người duyệt đã xác nhận (khi xuất bản).
create table if not exists knowledge (
  id            bigserial primary key,
  series_id     text not null references meeting_series(id),
  meeting_id    text not null references meetings(id),
  item_id       text not null,
  content       text not null,
  evidence      jsonb not null default '[]',
  confirmed_by  text,
  confirmed_at  timestamptz,
  unique (meeting_id, item_id)
);
create index if not exists knowledge_series_idx on knowledge (series_id);
create index if not exists meetings_series_idx on meetings (series_id);

-- RLS không policy: anon key / REST API của Supabase không đọc ghi được bảng nào.
-- Backend kết nối bằng user sở hữu bảng (DATABASE_URL) nên không bị chặn.
alter table meeting_series enable row level security;
alter table meetings       enable row level security;
alter table participants   enable row level security;
alter table utterances     enable row level security;
alter table events         enable row level security;
alter table items          enable row level security;
alter table evidence       enable row level security;
alter table review_actions enable row level security;
alter table consents       enable row level security;
alter table topic_maps     enable row level security;
alter table knowledge      enable row level security;
