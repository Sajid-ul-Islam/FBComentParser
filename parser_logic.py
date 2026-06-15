import re
import io
import openpyxl
import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

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
    out_sheet.append(["Commenter Name", "Comment", "Time Ago", "Brazil Goals", "Morocco Goals", "Verdict"])
    
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
                brazil, morocco = parse_score(comment_text)
                verdict = get_verdict(brazil, morocco)
                
                row_idx = out_sheet.max_row + 1
                name_cell = out_sheet.cell(row=row_idx, column=1, value=current_name)
                if current_link:
                    name_cell.hyperlink = current_link
                    name_cell.style = "Hyperlink"
                out_sheet.cell(row=row_idx, column=2, value=ILLEGAL_CHARACTERS_RE.sub(r'', comment_text))
                out_sheet.cell(row=row_idx, column=3, value=time_ago)
                out_sheet.cell(row=row_idx, column=4, value=brazil if brazil is not None else '-')
                out_sheet.cell(row=row_idx, column=5, value=morocco if morocco is not None else '-')
                out_sheet.cell(row=row_idx, column=6, value=verdict)
                
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

def pick_winners(df, actual_brazil, actual_morocco, max_winners=10):
    """Filter for exact score predictions and randomly select up to max_winners"""
    if df.empty:
        return pd.DataFrame()
        
    # Clean df to only include rows where goals are numeric (handles the '-' placeholder)
    df_clean = df[pd.to_numeric(df['Brazil Goals'], errors='coerce').notnull()]
    
    if df_clean.empty:
        return pd.DataFrame()
        
    # Filter for exact score match
    correct_df = df_clean[
        (df_clean['Brazil Goals'] == actual_brazil) & 
        (df_clean['Morocco Goals'] == actual_morocco)
    ]
    
    if correct_df.empty:
        return correct_df
        
    # Pick random winners
    winners = correct_df.sample(n=min(len(correct_df), max_winners))
    return winners
