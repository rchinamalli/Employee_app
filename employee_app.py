from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).parent / "employees.csv"
COLUMNS = [
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "department",
    "job_title",
    "employment_type",
    "hire_date",
    "base_salary",
    "bonus",
    "created_on",
    "updated_on",
]
DEPARTMENTS = ["Engineering", "Finance", "HR", "Marketing", "Operations", "Sales", "Other"]
EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Intern"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"[\d\s()+\-]{7,20}")


def load_employees() -> pd.DataFrame:
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, dtype=str).fillna("")
    return pd.DataFrame(columns=COLUMNS)


def save_employees(df: pd.DataFrame) -> None:
    df[COLUMNS].to_csv(DATA_FILE, index=False)


def add_employee(record: dict) -> None:
    save_employees(pd.concat([load_employees(), pd.DataFrame([record])], ignore_index=True))


def update_employee(employee_id: str, changes: dict) -> None:
    df = load_employees()
    for column, value in changes.items():
        df.loc[df["employee_id"] == employee_id, column] = value
    save_employees(df)


def validate(record: dict, existing: pd.DataFrame | None = None) -> list[str]:
    """Validate a record. Pass `existing` only when adding, to check the ID is unique."""
    errors = []
    if existing is not None:
        if not record["employee_id"]:
            errors.append("Employee ID is required.")
        elif record["employee_id"] in existing["employee_id"].values:
            errors.append(f"Employee ID {record['employee_id']} already exists.")
    if not record["first_name"] or not record["last_name"]:
        errors.append("First and last name are required.")
    if not EMAIL_RE.match(record["email"]):
        errors.append("Enter a valid email address.")
    if record["phone"] and not PHONE_RE.fullmatch(record["phone"]):
        errors.append("Enter a valid phone number.")
    if not record["job_title"]:
        errors.append("Job title is required.")
    return errors


def with_total_compensation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["base_salary"] = pd.to_numeric(out["base_salary"], errors="coerce").fillna(0.0)
    out["bonus"] = pd.to_numeric(out["bonus"], errors="coerce").fillna(0.0)
    out["total_compensation"] = out["base_salary"] + out["bonus"]
    return out


def employee_fields(prefix: str, current: dict | None = None) -> dict:
    """Render the shared employee inputs; `current` prefills them when updating."""
    cur = current or {}
    key = lambda name: f"{prefix}_{name}"  # noqa: E731

    col1, col2 = st.columns(2)
    first_name = col1.text_input("First name *", value=cur.get("first_name", ""), key=key("first"))
    last_name = col2.text_input("Last name *", value=cur.get("last_name", ""), key=key("last"))
    col3, col4 = st.columns(2)
    email = col3.text_input("Email *", value=cur.get("email", ""), key=key("email"))
    phone = col4.text_input("Phone", value=cur.get("phone", ""), key=key("phone"))

    col5, col6 = st.columns(2)
    dept_default = cur.get("department", DEPARTMENTS[0])
    department = col5.selectbox(
        "Department",
        DEPARTMENTS,
        index=DEPARTMENTS.index(dept_default) if dept_default in DEPARTMENTS else 0,
        key=key("dept"),
    )
    job_title = col6.text_input("Job title *", value=cur.get("job_title", ""), key=key("title"))

    col7, col8 = st.columns(2)
    type_default = cur.get("employment_type", EMPLOYMENT_TYPES[0])
    employment_type = col7.selectbox(
        "Employment type",
        EMPLOYMENT_TYPES,
        index=EMPLOYMENT_TYPES.index(type_default) if type_default in EMPLOYMENT_TYPES else 0,
        key=key("type"),
    )
    hire_date = col8.date_input(
        "Hire date",
        value=date.fromisoformat(cur["hire_date"]) if cur.get("hire_date") else date.today(),
        min_value=date(1970, 1, 1),
        max_value=date.today() + timedelta(days=365),
        key=key("hired"),
    )

    col9, col10 = st.columns(2)
    base_salary = col9.number_input(
        "Base salary (annual)",
        min_value=0.0,
        step=1000.0,
        format="%.2f",
        value=float(cur.get("base_salary") or 0.0),
        key=key("salary"),
    )
    bonus = col10.number_input(
        "Bonus (annual)",
        min_value=0.0,
        step=500.0,
        format="%.2f",
        value=float(cur.get("bonus") or 0.0),
        key=key("bonus"),
    )
    return {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "department": department,
        "job_title": job_title.strip(),
        "employment_type": employment_type,
        "hire_date": hire_date.isoformat(),
        "base_salary": f"{base_salary:.2f}",
        "bonus": f"{bonus:.2f}",
    }


st.set_page_config(page_title="Employee Information", page_icon="👥", layout="centered")
st.title("👥 Employee Information")

tab_add, tab_update, tab_inquiry = st.tabs(["Add employee", "Update employee", "Inquiry"])

with tab_add:
    # The form is only reset after a successful save (by bumping this counter, which
    # changes every widget key), so entries survive a validation error.
    version = st.session_state.setdefault("add_version", 0)
    if "add_saved" in st.session_state:
        st.success(st.session_state.pop("add_saved"))

    with st.form("add_form"):
        employee_id = st.text_input("Employee ID *", key=f"add{version}_id")
        fields = employee_fields(f"add{version}")
        submitted = st.form_submit_button("Save employee", type="primary")

    if submitted:
        today = date.today().isoformat()
        record = {
            "employee_id": employee_id.strip(),
            **fields,
            "created_on": today,
            "updated_on": today,
        }
        errors = validate(record, load_employees())
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            add_employee(record)
            st.session_state["add_saved"] = (
                f"Saved {record['first_name']} {record['last_name']} to {DATA_FILE.name}."
            )
            st.session_state["add_version"] = version + 1
            st.rerun()

with tab_update:
    employees = load_employees()
    if employees.empty:
        st.info("No employees yet. Add one first.")
    else:
        labels = {
            row.employee_id: f"{row.employee_id} – {row.first_name} {row.last_name}"
            for row in employees.itertuples()
        }
        selected = st.selectbox(
            "Select employee", list(labels), format_func=labels.get, key="update_select"
        )
        current = employees[employees["employee_id"] == selected].iloc[0].to_dict()

        with st.form("update_form"):
            st.text_input("Employee ID", value=selected, disabled=True)
            # Keyed per employee so the inputs reload when the selection changes.
            changes = employee_fields(f"upd_{selected}", current)
            updated = st.form_submit_button("Update employee", type="primary")

        if updated:
            errors = validate({"employee_id": selected, **changes})
            if errors:
                for msg in errors:
                    st.error(msg)
            else:
                update_employee(selected, {**changes, "updated_on": date.today().isoformat()})
                st.success(f"Updated {labels[selected]}.")

with tab_inquiry:
    results = with_total_compensation(load_employees())
    st.caption(f"{len(results)} employee(s) stored in {DATA_FILE.name}")

    query = st.text_input("Search by ID, name, email or job title")
    departments = st.multiselect("Department", DEPARTMENTS)
    if not results.empty and results["total_compensation"].max() > 0:
        top = float(results["total_compensation"].max())
        low, high = st.slider(
            "Total compensation range", 0.0, top, (0.0, top), step=max(top / 100, 1.0)
        )
        results = results[results["total_compensation"].between(low, high)]

    if query:
        needle = query.lower()
        haystack = results[["employee_id", "first_name", "last_name", "email", "job_title"]]
        results = results[
            haystack.apply(lambda row: needle in " ".join(row).lower(), axis=1)
        ]
    if departments:
        results = results[results["department"].isin(departments)]

    st.dataframe(
        results,
        width="stretch",
        hide_index=True,
        column_config={
            "base_salary": st.column_config.NumberColumn("Base salary", format="%.2f"),
            "bonus": st.column_config.NumberColumn("Bonus", format="%.2f"),
            "total_compensation": st.column_config.NumberColumn("Total comp.", format="%.2f"),
        },
    )
    if not results.empty:
        st.download_button(
            "Download CSV",
            results.to_csv(index=False),
            file_name="employees.csv",
            mime="text/csv",
        )
