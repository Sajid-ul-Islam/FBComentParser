import streamlit as st
import pandas as pd
import re
import io
import openpyxl
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from collections import Counter

st.set_page_config(page_title="Football Prediction Analyzer", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for polish ---
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Football Prediction Analyzer")
st.markdown("Easily extract, analyze, and export predictions from social media comments.")
st.divider()

# Sidebar
with st.sidebar:
    st.header("📋 About")
    st.info("This tool helps you quickly turn messy social media comment blocks into structured Excel/CSV data.")
    
    with st.expander("📝 Formatting Guide", expanded=True):
        st.markdown("""
        **How to copy comments:**
        Simply highlight the comment section on Facebook/WhatsApp and copy.
        
        **Expected Format:**
        ```text
        Name Surname
        Brazil 2-1 Morocco
        1d
        Reply
        ```
        """)
    st.markdown("---")
    st.caption("Built with Streamlit & ❤️")

# Main input area
tab1, tab2 = st.tabs(["📝 Paste Text Analysis", "📁 Excel File Analysis"])

with tab1:
    input_text = st.text_area(
        "📝 Paste your comments here:",
        height=400,
        placeholder="""
Example:
Samiul Islam
My prediction:
Brazil🇧🇷 2-1Morocco🇲🇦
1d
Reply
Shadin Mahbub
Brazil 2-1 Morocco
1d
Reply
    """
    )

def extract_name_and_prediction(text):
    """Extract name and prediction from comment blocks"""
    lines = text.strip().split('\n')
    results = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if line looks like a name (not containing numbers or common prediction patterns)
        is_name = (
            len(line) > 2 and 
            not re.search(r'\d+[dmhyw]$', line) and # Exclude timestamps like 1d, 2h, 5m
            not re.search(r'Brazil|Morocco|ব্রাজিল|মরক্কো', line, re.IGNORECASE) and
            not re.search(r'goal|গোল|prediction', line, re.IGNORECASE) and
            line not in ['Reply', 'Edited', 'See Original', 'Top fan', 'Follow', 'Like'] and
            not re.search(r'^[\W_]+$', line) # Exclude lines with only emojis/punctuation
        )
        
        if is_name:
            name = line
            # Look ahead for prediction
            prediction = ""
            lines_to_skip = 0
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                # Check if this line contains a score prediction
                if re.search(r'\d+\s*[-–:]\s*\d+', next_line):
                    prediction = next_line
                    lines_to_skip = j - i
                    break
                elif re.search(r'Brazil.*\d.*Morocco|ব্রাজিল.*\d.*মরক্কো', next_line, re.IGNORECASE):
                    prediction = next_line
                    lines_to_skip = j - i
                    break
            
            # If no prediction found in next lines, check current line
            if not prediction and re.search(r'\d+\s*[-–:]\s*\d+', line):
                prediction = line
            
            results.append({
                'name': name,
                'raw_prediction': prediction
            })
            if lines_to_skip > 0:
                i += lines_to_skip + 1
            else:
                i += 1
        else:
            i += 1
    
    return results

def parse_score(prediction):
    """Extract Brazil and Morocco scores from prediction text"""
    if not prediction:
        return None, None
    
    # Pattern for "Brazil 2-1 Morocco" or "ব্রাজিল ২-১ মরক্কো"
    patterns = [
        r'Brazil[^\d]*(\d+)\s*[-–:]\s*(\d+)[^\d]*Morocco',
        r'ব্রাজিল[^\d]*(\d+)\s*[-–:]\s*(\d+)[^\d]*মরক্কো',
        r'(\d+)\s*[-–:]\s*(\d+)',  # Just numbers like "2-1"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prediction, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def get_verdict(brazil_score, morocco_score):
    """Generate verdict based on prediction"""
    if brazil_score is None or morocco_score is None:
        return "❓ Invalid Prediction"
    
    if brazil_score > morocco_score:
        return "✅ Brazil Win"
    elif morocco_score > brazil_score:
        return "❌ Morocco Win (Upset)"
    else:
        return "🤝 Draw"

def process_excel_file(uploaded_file):
    """Parse raw excel file and extract formatted commenter info"""
    wb = openpyxl.load_workbook(uploaded_file)
    sheet = wb.active
    
    out_wb = openpyxl.Workbook()
    out_sheet = out_wb.active
    out_sheet.append(["Commenter Name", "Comment", "Time Ago"])
    
    current_name = None
    current_link = None
    current_comment_lines = []
    
    for row in sheet.iter_rows():
        if not row: continue
        cell = row[0]
        val = cell.value
        if val is None: continue
        
        val = str(val).strip()
        if not val: continue
        
        link = cell.hyperlink.target if cell.hyperlink else None
        
        if re.match(r'^\d+\s*[dmhyws]$', val, re.IGNORECASE) or val.lower() == 'just now':
            time_ago = val
            if current_name:
                comment_text = "\\n".join(current_comment_lines)
                row_idx = out_sheet.max_row + 1
                name_cell = out_sheet.cell(row=row_idx, column=1, value=current_name)
                if current_link:
                    name_cell.hyperlink = current_link
                    name_cell.style = "Hyperlink"
                out_sheet.cell(row=row_idx, column=2, value=ILLEGAL_CHARACTERS_RE.sub(r'', comment_text))
                out_sheet.cell(row=row_idx, column=3, value=time_ago)
                
            current_name = None
            current_link = None
            current_comment_lines = []
        elif val in ['Reply', 'Hide', 'Send message', 'See Translation', 'Edited', 'Top fan', 'Follow', 'Like']:
            continue
        else:
            if not current_name:
                current_name = val
                current_link = link
            else:
                current_comment_lines.append(val)
                
    output = io.BytesIO()
    out_wb.save(output)
    output.seek(0)
    
    preview_df = pd.read_excel(output)
    output.seek(0)
    
    return output, preview_df

    # Analyze button
    if st.button("🔍 Analyze Predictions", type="primary", use_container_width=True):
        if not input_text.strip():
            st.warning("Please paste some comments first!")
        else:
            # Extract data
            raw_results = extract_name_and_prediction(input_text)
            
            # Parse scores
            parsed_results = []
            for item in raw_results:
                brazil, morocco = parse_score(item['raw_prediction'])
                parsed_results.append({
                    'Name': item['name'],
                    'Prediction Text': item['raw_prediction'][:100] if item['raw_prediction'] else 'Not found',
                    'Brazil Goals': brazil if brazil is not None else '-',
                    'Morocco Goals': morocco if morocco is not None else '-',
                    'Verdict': get_verdict(brazil, morocco)
                })
            
            # Filter out entries with no name or completely invalid
            valid_results = [r for r in parsed_results if r['Name'] and r['Brazil Goals'] != '-']
            invalid_results = [r for r in parsed_results if r['Name'] and r['Brazil Goals'] == '-']
            
            # Create DataFrame
            if not valid_results:
                df = pd.DataFrame(columns=['Name', 'Prediction Text', 'Brazil Goals', 'Morocco Goals', 'Verdict'])
                st.warning("No valid predictions could be parsed from the text.")
            else:
                df = pd.DataFrame(valid_results)
                st.toast(f"Successfully parsed {len(valid_results)} predictions!", icon="🎉")
            
            # Display statistics
            st.subheader("📊 Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Valid Predictions", len(valid_results))
            with col2:
                brazil_wins = sum(1 for r in valid_results if r['Verdict'] == "✅ Brazil Win")
                st.metric("Brazil Win Predictions", brazil_wins)
            with col3:
                morocco_wins = sum(1 for r in valid_results if r['Verdict'] == "❌ Morocco Win (Upset)")
                st.metric("Morocco Win Predictions", morocco_wins)
            with col4:
                draws = sum(1 for r in valid_results if r['Verdict'] == "🤝 Draw")
                st.metric("Draw Predictions", draws)
            
            # Goal distribution charts
            st.subheader("📈 Goal Distribution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                brazil_goals = [r['Brazil Goals'] for r in valid_results if isinstance(r['Brazil Goals'], int)]
                if brazil_goals:
                    goal_counts = Counter(brazil_goals)
                    st.bar_chart(pd.DataFrame.from_dict(goal_counts, orient='index', columns=['Count']))
            
            with col2:
                total_goals = [r['Brazil Goals'] + r['Morocco Goals'] for r in valid_results if isinstance(r['Brazil Goals'], int) and isinstance(r['Morocco Goals'], int)]
                if total_goals:
                    goal_counts = Counter(total_goals)
                    st.bar_chart(pd.DataFrame.from_dict(goal_counts, orient='index', columns=['Count']))
            
            # Most common scorelines
            st.subheader("🎯 Most Common Scoreline Predictions")
            scorelines = [f"{r['Brazil Goals']}-{r['Morocco Goals']}" for r in valid_results if isinstance(r['Brazil Goals'], int)]
            if scorelines:
                common = Counter(scorelines).most_common(5)
                for score, count in common:
                    st.write(f"**{score}** → {count} predictions")
            
            # Display the main table
            st.subheader("📋 All Predictions")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Prediction Text": st.column_config.TextColumn("Raw Prediction", width="large"),
                    "Brazil Goals": st.column_config.NumberColumn("Brazil", width="small"),
                    "Morocco Goals": st.column_config.NumberColumn("Morocco", width="small"),
                    "Verdict": st.column_config.TextColumn("Verdict", width="medium"),
                }
            )
            
            # Show invalid predictions
            if invalid_results:
                with st.expander("⚠️ Unparsed Comments (needs manual review)"):
                    for inv in invalid_results:
                        st.write(f"**{inv['Name']}**: {inv['Prediction Text']}")
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            with col1:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="predictions_analysis.csv",
                    mime="text/csv",
                )
                
            with col2:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Predictions')
                st.download_button(
                    label="📊 Download as Excel",
                    data=buffer.getvalue(),
                    file_name="predictions_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

with tab2:
    st.markdown("### 📁 Upload Raw Comments Excel File")
    st.info("Upload a raw single-column Excel file containing comments (like `Sample.xlsx`) to parse it into structured columns with working hyperlinks.")
    uploaded_file = st.file_uploader("Choose an Excel file (.xlsx)", type=['xlsx'])
    
    if uploaded_file is not None:
        if st.button("⚙️ Process Excel File", type="primary", use_container_width=True):
            with st.spinner("Processing your file..."):
                try:
                    output_buffer, preview_df = process_excel_file(uploaded_file)
                    st.toast("File processed successfully!", icon="✅")
                    
                    st.subheader("📊 Extraction Summary")
                    st.metric("Total Comments Extracted", len(preview_df))
                    
                    st.subheader("Preview (first 10 rows)")
                    st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
                    
                    st.download_button(
                        label="📥 Download Analyzed Excel File",
                        data=output_buffer,
                        file_name="Analyzed_" + uploaded_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")