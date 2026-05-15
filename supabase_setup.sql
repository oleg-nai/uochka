-- Enable PostGIS
create extension if not exists postgis;

-- Tables
create table if not exists users (
    id bigserial primary key,
    telegram_id bigint unique not null,
    username text,
    created_at timestamptz default now(),
    is_banned boolean default false
);

create table if not exists toilets (
    id bigserial primary key,
    location geography(point, 4326) not null,
    name text,
    address text,
    is_paid boolean default false,
    is_accessible boolean default false,
    working_hours text,
    verified boolean default false,
    reports_count int default 0,
    hidden_at timestamptz,
    created_at timestamptz default now()
);

create table if not exists reviews (
    id bigserial primary key,
    toilet_id bigint references toilets(id) on delete cascade,
    user_id bigint references users(id) on delete cascade,
    rating int check (rating between 1 and 5),
    comment text,
    created_at timestamptz default now()
);

create table if not exists reports (
    id bigserial primary key,
    toilet_id bigint references toilets(id) on delete cascade,
    user_id bigint references users(id) on delete cascade,
    reason text check (reason in ('closed', 'not_exist', 'dirty')),
    created_at timestamptz default now()
);

-- Spatial index
create index if not exists toilets_location_idx on toilets using gist(location);

-- Function: find nearest toilets (returns id, lat, lon, distance_m, name, address, is_paid)
create or replace function find_nearest_toilets(
    user_lat float8,
    user_lon float8,
    result_limit int default 5
)
returns table (
    id bigint,
    lat float8,
    lon float8,
    distance_m float8,
    name text,
    address text,
    is_paid boolean
)
language sql stable
as $$
    select
        t.id,
        st_y(t.location::geometry) as lat,
        st_x(t.location::geometry) as lon,
        st_distance(t.location, st_makepoint(user_lon, user_lat)::geography) as distance_m,
        t.name,
        t.address,
        t.is_paid
    from toilets t
    where
        t.hidden_at is null
        and st_dwithin(t.location, st_makepoint(user_lon, user_lat)::geography, 5000)
    order by distance_m
    limit result_limit;
$$;

-- Function: hide toilet if 3+ reports in last 7 days
create or replace function maybe_hide_toilet(p_toilet_id bigint)
returns void
language plpgsql
as $$
declare
    recent_count int;
begin
    select count(*) into recent_count
    from reports
    where toilet_id = p_toilet_id
      and created_at > now() - interval '7 days';

    if recent_count >= 3 then
        update toilets
        set hidden_at = now(), reports_count = recent_count
        where id = p_toilet_id and hidden_at is null;
    else
        update toilets set reports_count = recent_count where id = p_toilet_id;
    end if;
end;
$$;
