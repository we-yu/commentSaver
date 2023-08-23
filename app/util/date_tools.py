
def convert_jp_weekday_to_en(date_str):
    weekdays_jp_to_en = {
        '(日)': '(Sun)',
        '(月)': '(Mon)',
        '(火)': '(Tue)',
        '(水)': '(Wed)',
        '(木)': '(Thu)',
        '(金)': '(Fri)',
        '(土)': '(Sat)'
    }
    
    for jp, en in weekdays_jp_to_en.items():
        date_str = date_str.replace(jp, en)
    return date_str

