import streamlit as st
import json

from src.rag.llm_service import LLMService

from src.database.db_manager import (
    save_study_plan,
    get_study_plans,
    delete_study_plan
)

st.set_page_config(
    page_title="Study Planner",
    page_icon="📅",
    layout="wide"
)

st.title("📅 AI Study Planner")

if "user" not in st.session_state:
    st.warning("Please login first.")
    st.stop()

user_id = st.session_state["user"]["id"]

tab1, tab2 = st.tabs(
    ["➕ Create Plan", "📚 Saved Plans"]
)

# ======================================
# CREATE PLAN
# ======================================

with tab1:

    st.subheader("Generate Personalized Study Plan")

    subject = st.text_input(
        "Subject"
    )

    exam_date = st.date_input(
        "Exam Date"
    )

    daily_hours = st.slider(
        "Daily Study Hours",
        1.0,
        12.0,
        3.0
    )

    difficulty = st.selectbox(
        "Difficulty",
        [
            "Easy",
            "Medium",
            "Hard"
        ]
    )

    goals = st.text_area(
        "Goals",
        placeholder="Example: Score above 90%, complete all units, master problem solving..."
    )

    if st.button(
        "🚀 Generate Study Plan",
        use_container_width=True
    ):

        if not subject:
            st.error("Please enter subject.")
            st.stop()

        try:

            with st.spinner("Generating study plan..."):

                llm = LLMService()

                plan = llm.generate_study_plan(
                    subject,
                    str(exam_date),
                    daily_hours,
                    difficulty,
                    goals
                )

                st.markdown(plan)

                save_study_plan(
                    user_id,
                    subject,
                    str(exam_date),
                    daily_hours,
                    difficulty,
                    goals,
                    json.dumps(
                        {"plan": plan}
                    )
                )

                st.success(
                    "Study Plan Saved Successfully!"
                )

        except Exception as e:
            st.error(str(e))

# ======================================
# SAVED PLANS
# ======================================

with tab2:

    plans = get_study_plans(user_id)

    if not plans:
        st.info("No study plans found.")
    else:

        for plan in plans:

            with st.expander(
                f"{plan['subject']} | {plan['exam_date']}"
            ):

                data = json.loads(
                    plan["plan_json"]
                )

                st.markdown(
                    data["plan"]
                )

                if st.button(
                    f"Delete Plan {plan['id']}"
                ):

                    delete_study_plan(
                        user_id,
                        plan["id"]
                    )

                    st.rerun()