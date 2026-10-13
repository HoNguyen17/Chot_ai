-- Chốt — schema v1 (PostgreSQL 15+ / Supabase). Xem docs/DATA_DESIGN.md#database.
-- Chạy: psql "$DATABASE_URL" -f db/migrations/001_init.sql   (Supabase: dán vào SQL editor)

create extension if not exists vector;   -- pgvector, dùng ở bước 2 (tra cứu xuyên cuộc họp)

-- Một nhóm họp định kỳ (vd "Weekly sync team App"). Ledger xuyên cuộc họp nối theo series.
create table if not exists meeting_series (
  id          text primary key,
  name        text not null,
  created_at  timestamptz not null default now()
);

create table if not exists meetings (
  id            text primary key,
  series_id     text references meeting_series(id),
  title         text,
  meeting_date  date,
  generated_by  text not null,              -- "rules-v1+llm-events" | "keyword-baseline" ...
  published     boolean not null default false,
  published_at  timestamptz,
  created_at    timestamptz not null default now()
);

create table if not exists participants (
  meeting_id  text not null references meetings(id) on delete cascade,
  name        text not null,
  role        text,
  is_chair    boolean not null default false,
  absent      boolean not null default false,
  primary key (meeting_id, name)
);

create table if not exists utterances (
  meeting_id  text not null references meetings(id) on delete cascade,
  id          text not null,                 -- "u001"
  idx         int  not null,
  ts_seconds  int  not null,
  speaker     text not null,
  text        text not null,
  primary key (meeting_id, id)
);

-- Sự kiện do LLM gán nhãn: lưu lại để replay khi sửa luật, và để debug.
create table if not exists events (
  id             bigserial primary key,
  meeting_id     text not null references meetings(id) on delete cascade,
  utt_id         text not null,
  thread         text not null,
  kind           text not null check (kind in (
                   'propose','revise','object','agree','defer','reopen',
                   'assign','commit','decline','blocker','question','info','request','feedback')),
  speaker        text not null,
  key            text,
  content        text not null default '',
  hedged         boolean not null default false,
  owner          text,
  deadline_text  text,
  quote          text not null default '',
  foreign key (meeting_id, utt_id) references utterances(meeting_id, id) on delete cascade
);

create table if not exists items (
  meeting_id    text not null references meetings(id) on delete cascade,
  id            text not null,               -- "D1", "T2"...
  type          text not null check (type in (
                  'decision','option','task','blocker','open_question','knowledge','request','feedback')),
  status        text not null check (status in (
                  'final','needs_confirmation','superseded','rejected','deferred','open')),
  thread        text,
  content       text not null,
  owner         text,
  decided_by    text,
  deadline      date,
  deadline_text text,
  supersedes    text[] not null default '{}',
  flags         text[] not null default '{}',
  confidence    real,
  approved      boolean not null default false,
  embedding     vector(1024),                -- bge-m3; NULL ở v1
  primary key (meeting_id, id)
);
create index if not exists items_open_idx on items (status) where status in ('needs_confirmation','deferred','open');

create table if not exists evidence (
  meeting_id  text not null,
  item_id     text not null,
  utt_id      text not null,
  quote       text not null,
  primary key (meeting_id, item_id, utt_id),
  foreign key (meeting_id, item_id) references items(meeting_id, id) on delete cascade,
  foreign key (meeting_id, utt_id) references utterances(meeting_id, id) on delete cascade
);

-- Nhật ký duyệt: append-only. Đây vừa là audit trail vừa là dữ liệu đánh giá / cải tiến.
create table if not exists review_actions (
  id          bigserial primary key,
  meeting_id  text not null references meetings(id) on delete cascade,
  item_id     text not null,
  field       text not null,
  old_value   text,
  new_value   text,
  reviewer    text,
  at          timestamptz not null default now()
);

-- Consent theo từng mục đích (Luật 91/2025/QH15): tách transcript, xử lý AI, lưu kho tri thức.
create table if not exists consents (
  meeting_id  text not null references meetings(id) on delete cascade,
  person      text not null,
  purpose     text not null check (purpose in ('transcript','ai_processing','knowledge_base')),
  granted     boolean not null,
  at          timestamptz not null default now(),
  primary key (meeting_id, person, purpose)
);
