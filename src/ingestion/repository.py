from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg


@dataclass(frozen=True)
class IngestionResult:
    batch_id: str
    source_file: str
    row_count: int
    feature_count: int


def initialize_schema(database_url: str) -> None:
    statements = [
        """
        create table if not exists ingestion_batches (
            batch_id text primary key,
            source_file text not null,
            source_hash text not null,
            row_count integer not null,
            status text not null,
            ingested_at timestamptz not null default now()
        )
        """,
        """
        create table if not exists ai4i_machine_observations (
            udi integer primary key,
            product_id text not null,
            product_type text not null,
            air_temperature_k double precision not null,
            process_temperature_k double precision not null,
            rotational_speed_rpm double precision not null,
            torque_nm double precision not null,
            tool_wear_min double precision not null,
            machine_failure integer not null,
            twf integer not null,
            hdf integer not null,
            pwf integer not null,
            osf integer not null,
            rnf integer not null,
            batch_id text not null references ingestion_batches(batch_id),
            ingested_at timestamptz not null default now()
        )
        """,
        """
        create table if not exists ai4i_machine_features (
            udi integer primary key references ai4i_machine_observations(udi),
            product_type text not null,
            air_temperature_k double precision not null,
            process_temperature_k double precision not null,
            temperature_delta_k double precision not null,
            rotational_speed_rpm double precision not null,
            rotational_speed_rad_s double precision not null,
            torque_nm double precision not null,
            tool_wear_min double precision not null,
            power_w double precision not null,
            torque_speed_interaction double precision not null,
            tool_wear_by_torque double precision not null,
            temperature_delta_low_flag integer not null,
            power_low_flag integer not null,
            power_high_flag integer not null,
            overstrain_threshold double precision not null,
            overstrain_margin double precision not null,
            type_h integer not null,
            type_l integer not null,
            type_m integer not null,
            machine_failure integer not null,
            batch_id text not null references ingestion_batches(batch_id),
            updated_at timestamptz not null default now()
        )
        """,
    ]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()


def upsert_ai4i_dataset(
    *,
    database_url: str,
    batch_id: str,
    source_file: str | Path,
    source_hash: str,
    observations: pd.DataFrame,
    features: pd.DataFrame,
) -> IngestionResult:
    source_name = str(source_file)
    initialize_schema(database_url)

    observation_rows = [
        (
            int(row.udi),
            row.product_id,
            row.product_type,
            float(row.air_temperature_k),
            float(row.process_temperature_k),
            float(row.rotational_speed_rpm),
            float(row.torque_nm),
            float(row.tool_wear_min),
            int(row.machine_failure),
            int(row.twf),
            int(row.hdf),
            int(row.pwf),
            int(row.osf),
            int(row.rnf),
            batch_id,
        )
        for row in observations.itertuples(index=False)
    ]

    feature_rows = [
        (
            int(row.udi),
            row.product_type,
            float(row.air_temperature_k),
            float(row.process_temperature_k),
            float(row.temperature_delta_k),
            float(row.rotational_speed_rpm),
            float(row.rotational_speed_rad_s),
            float(row.torque_nm),
            float(row.tool_wear_min),
            float(row.power_w),
            float(row.torque_speed_interaction),
            float(row.tool_wear_by_torque),
            int(row.temperature_delta_low_flag),
            int(row.power_low_flag),
            int(row.power_high_flag),
            float(row.overstrain_threshold),
            float(row.overstrain_margin),
            int(row.type_H),
            int(row.type_L),
            int(row.type_M),
            int(row.machine_failure),
            batch_id,
        )
        for row in features.itertuples(index=False)
    ]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into ingestion_batches (
                    batch_id, source_file, source_hash, row_count, status
                )
                values (%s, %s, %s, %s, %s)
                on conflict (batch_id) do update set
                    source_file = excluded.source_file,
                    source_hash = excluded.source_hash,
                    row_count = excluded.row_count,
                    status = excluded.status,
                    ingested_at = now()
                """,
                (batch_id, source_name, source_hash, len(observation_rows), "ingested"),
            )
            cur.executemany(
                """
                insert into ai4i_machine_observations (
                    udi, product_id, product_type, air_temperature_k,
                    process_temperature_k, rotational_speed_rpm, torque_nm, tool_wear_min,
                    machine_failure, twf, hdf, pwf, osf, rnf, batch_id
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                on conflict (udi) do update set
                    product_id = excluded.product_id,
                    product_type = excluded.product_type,
                    air_temperature_k = excluded.air_temperature_k,
                    process_temperature_k = excluded.process_temperature_k,
                    rotational_speed_rpm = excluded.rotational_speed_rpm,
                    torque_nm = excluded.torque_nm,
                    tool_wear_min = excluded.tool_wear_min,
                    machine_failure = excluded.machine_failure,
                    twf = excluded.twf,
                    hdf = excluded.hdf,
                    pwf = excluded.pwf,
                    osf = excluded.osf,
                    rnf = excluded.rnf,
                    batch_id = excluded.batch_id,
                    ingested_at = now()
                """,
                observation_rows,
            )
            cur.executemany(
                """
                insert into ai4i_machine_features (
                    udi, product_type, air_temperature_k, process_temperature_k,
                    temperature_delta_k, rotational_speed_rpm, rotational_speed_rad_s,
                    torque_nm, tool_wear_min, power_w, torque_speed_interaction,
                    tool_wear_by_torque, temperature_delta_low_flag, power_low_flag,
                    power_high_flag, overstrain_threshold, overstrain_margin,
                    type_h, type_l, type_m, machine_failure, batch_id
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                on conflict (udi) do update set
                    product_type = excluded.product_type,
                    air_temperature_k = excluded.air_temperature_k,
                    process_temperature_k = excluded.process_temperature_k,
                    temperature_delta_k = excluded.temperature_delta_k,
                    rotational_speed_rpm = excluded.rotational_speed_rpm,
                    rotational_speed_rad_s = excluded.rotational_speed_rad_s,
                    torque_nm = excluded.torque_nm,
                    tool_wear_min = excluded.tool_wear_min,
                    power_w = excluded.power_w,
                    torque_speed_interaction = excluded.torque_speed_interaction,
                    tool_wear_by_torque = excluded.tool_wear_by_torque,
                    temperature_delta_low_flag = excluded.temperature_delta_low_flag,
                    power_low_flag = excluded.power_low_flag,
                    power_high_flag = excluded.power_high_flag,
                    overstrain_threshold = excluded.overstrain_threshold,
                    overstrain_margin = excluded.overstrain_margin,
                    type_h = excluded.type_h,
                    type_l = excluded.type_l,
                    type_m = excluded.type_m,
                    machine_failure = excluded.machine_failure,
                    batch_id = excluded.batch_id,
                    updated_at = now()
                """,
                feature_rows,
            )
        conn.commit()

    return IngestionResult(
        batch_id=batch_id,
        source_file=source_name,
        row_count=len(observation_rows),
        feature_count=len(feature_rows),
    )
