import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
import os

# --- Load previous submissions if they exist ---
if "submissions" not in st.session_state:
    if os.path.exists("submissions1.pkl"):
        st.session_state.submissions = pd.read_pickle("submissions1.pkl")
    else:
        st.session_state.submissions = pd.DataFrame(columns=[
            "title", "year", "collaborators", "category", "subject",
            "semester", "email", "file", "content"
        ])

# --- Email Notification Function ---
def send_email(to_email, subject, message):
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(message)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- Extract text from uploaded PDF ---
def extract_text_from_pdf(uploaded_file):
    text = ""
    if uploaded_file is not None:
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text

# --- Plagiarism Check ---
def check_plagiarism(new_text, existing_texts, existing_titles):
    if existing_texts:
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([new_text] + existing_texts)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
        results = list(zip(existing_titles, similarities))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    return []


# --- Streamlit UI ---
st.title("📚 InnoVault - Academic Repository")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Upload Work", "Search Past Work", "Check Plagiarism"])

# --- Home Page ---
if page == "Home":
    st.write("### Welcome to InnoVault")
    st.markdown(
        """
        A platform where students can:
        - 📤 Upload their work
        - 🔎 Search academic archives
        - 📬 Receive email confirmations
        - 🛡️ Check for plagiarism
        """
    )

# --- Upload Page ---
elif page == "Upload Work":
    st.subheader("Upload Your Work")
    title = st.text_input("Project/Paper Title")
    year = st.selectbox("Year", list(range(2015, 2026)))
    collaborators = st.text_area("Collaborators (comma-separated)")
    category = st.radio("Category", ["Project", "Paper"])
    subject = st.text_input("Subject")
    semester = st.selectbox("Semester", list(range(1, 9)))
    uploader_email = st.text_input("Your Email Address")
    uploaded_file = st.file_uploader("Upload PDF Document", type=["pdf"])

    if uploaded_file:
        document_text = extract_text_from_pdf(uploaded_file)
    else:
        document_text = ""

    if st.button("Upload"):
        if document_text and uploader_email:
            existing_texts = st.session_state.submissions["content"].tolist()
            existing_titles = st.session_state.submissions["title"].tolist()
            
            similarity_results = check_plagiarism(document_text, existing_texts, existing_titles)
            
            if similarity_results and similarity_results[0][1] > 0.7:
                st.error("⚠️ High plagiarism detected!")
                st.write("### Most Similar Documents:")
                for title, score in similarity_results[:5]:  # Top 5 matches
                    if score > 0.3:
                        st.write(f"- **{title}** – Similarity: {score * 100:.2f}%")
            else:
                # Proceed to save the new submission
                new_entry = pd.DataFrame({
                    "title": [title],
                    "year": [year],
                    "collaborators": [collaborators.split(',')],
                    "category": [category],
                    "subject": [subject],
                    "semester": [semester],
                    "email": [uploader_email],
                    "file": [uploaded_file.getvalue()],
                    "content": [document_text]
                })
                st.session_state.submissions = pd.concat([st.session_state.submissions, new_entry], ignore_index=True)
                st.success("✅ File uploaded successfully!")
                
                # Save to disk
                st.session_state.submissions.to_pickle("submissions1.pkl")

                # Send confirmation email
                try:
                    send_email(
                        uploader_email,
                        "InnoVault - Upload Confirmation",
                        f"Your document '{title}' has been successfully uploaded."
                    )
                    st.success("Confirmation email sent!")
                except Exception as e:
                    st.warning(f"Email not sent: {e}")
        else:
            st.error("Please upload a valid PDF and provide your email.")

# --- Search Page ---
elif page == "Search Past Work":
    st.subheader("Search Past Work")
    search_query = st.text_input("Search by Title or Collaborator Name")
    search_year = st.selectbox("Filter by Year", ["All"] + list(range(2015, 2026)))
    category_filter = st.radio("Filter by Category", ["All", "Project", "Paper"])

    filtered = st.session_state.submissions.copy()
    if search_year != "All":
        filtered = filtered[filtered["year"] == search_year]
    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]
    if search_query:
        filtered = filtered[
            filtered["title"].str.contains(search_query, case=False, na=False) |
            filtered["collaborators"].apply(lambda x: any(search_query.lower() in name.lower() for name in x))
        ]

    for i, row in filtered.iterrows():
        with st.expander(f"📄 {row['title']} (by {', '.join(row['collaborators'])})"):
            st.write(f"**Subject:** {row['subject']}")
            st.write(f"**Semester:** {row['semester']}")
            st.write(f"**Category:** {row['category']}")
            st.write(f"**Year:** {row['year']}")
            st.download_button(
                label="📥 Download PDF",
                data=row["file"],
                file_name=row["title"] + ".pdf",
                mime="application/pdf"
            )

            message_to_send = st.text_area(f"Message to send to collaborators of '{row['title']}'", key=f"msg_{i}")
            if st.button(f"Send Email to Collaborators", key=f"email_{i}"):
                try:
                    collaborator_email=row['email'] 
                    send_email(
                        to_email=collaborator_email,
                        subject=f"Inquiry about '{row['title']}'",
                        message=message_to_send if message_to_send else "Hello, I'm interested in your submission on InnoVault!"
                    )
                    st.success(f"Email sent to: {', '.join(row['collaborators'])}")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")


elif page == "Check Plagiarism":
    st.subheader("🔍 Direct Plagiarism Check")
    check_file = st.file_uploader("Upload a PDF Document to Check", type=["pdf"])

    if check_file:
        check_text = extract_text_from_pdf(check_file)
        existing_texts = st.session_state.submissions["content"].tolist()
        existing_titles = st.session_state.submissions["title"].tolist()

        similarity_results = check_plagiarism(check_text, existing_texts, existing_titles)

        if similarity_results:
            top_score = similarity_results[0][1]

            if top_score > 0.7:
                st.error(f"⚠️ High plagiarism detected! Top Similarity: {top_score * 100:.2f}%")
            elif top_score > 0.3:
                st.warning(f"⚠️ Moderate similarity found. Top Similarity: {top_score * 100:.2f}%")
            else:
                st.success(f"✅ No significant plagiarism found. Top Similarity: {top_score * 100:.2f}%")

            st.write("### 🔗 Most Similar Documents:")
            for title, score in similarity_results[:5]:
                if score > 0.5:
                    match = st.session_state.submissions[st.session_state.submissions["title"] == title].iloc[0]
                    with st.expander(f"📄 {match['title']} – Similarity: {score * 100:.2f}%"):
                        st.write(f"**Subject:** {match['subject']}")
                        st.write(f"**Semester:** {match['semester']}")
                        st.write(f"**Category:** {match['category']}")
                        st.write(f"**Year:** {match['year']}")
                        st.write(f"**Collaborators:** {', '.join(match['collaborators'])}")
                        st.download_button(
                            label="📥 Download PDF",
                            data=match["file"],
                            file_name=match["title"] + ".pdf",
                            mime="application/pdf"
                        )
        else:
            st.success("✅ No similar documents found.")
    else:
        st.info("📄 Please upload a PDF document to begin plagiarism check.")
