from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from bson import ObjectId

main_bp = Blueprint('main', __name__)

def get_grade_point(mark):
    if mark == 'Not provided' or mark is None:
        return None
    try:
        mark = int(mark)
    except:
        return None
    if mark >= 90:   return 10.0
    elif mark >= 80: return round(8.0 + (mark - 80) * 0.09, 2)
    elif mark >= 75: return round(7.5 + (mark - 75) * 0.1, 2)
    elif mark >= 70: return round(7.0 + (mark - 70) * 0.1, 2)
    elif mark >= 60: return round(6.0 + (mark - 60) * 0.1, 2)
    elif mark >= 50: return round(5.0 + (mark - 50) * 0.1, 2)
    elif mark >= 40: return round(4.0 + (mark - 40) * 0.1, 2)
    else:            return 0.0

def compute_cgpa(semesters):
    total_cp = 0
    total_c  = 0
    for sem_key in ['sem1','sem2','sem3','sem4','sem5','sem6']:
        for subj in semesters.get(sem_key, []):
            mark = subj.get('mark')
            if mark == 'Not provided' or mark is None:
                continue
            credit = subj.get('credit', 3)
            gp = get_grade_point(mark)
            if gp is not None:
                total_cp += credit * gp
                total_c  += credit
    return round(total_cp / total_c, 2) if total_c > 0 else None

def get_arrears(semesters):
    arrears = []
    sem_labels = {'sem1':'Semester 1','sem2':'Semester 2','sem3':'Semester 3',
                  'sem4':'Semester 4','sem5':'Semester 5','sem6':'Semester 6'}
    for sem_key in ['sem1','sem2','sem3','sem4','sem5','sem6']:
        for subj in semesters.get(sem_key, []):
            mark = subj.get('mark')
            if mark == 'Not provided' or mark is None:
                continue
            try:
                if int(mark) < 40:
                    arrears.append({
                        'sem_key': sem_key,
                        'sem_label': sem_labels[sem_key],
                        'subject': subj.get('subject'),
                        'mark': mark,
                        'cleared': subj.get('cleared', False)
                    })
            except:
                pass
    return arrears

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    stats = {
        'total': db.students.count_documents({}),
        'first_year': db.students.count_documents({'year': 'First Year'}),
        'second_year': db.students.count_documents({'year': 'Second Year'}),
        'third_year': db.students.count_documents({'year': 'Third Year'}),
    }
    all_students = list(db.students.find({}, {'semesters': 1}))
    arrear_count = sum(1 for s in all_students if get_arrears(s.get('semesters', {})))
    return render_template('dashboard.html', stats=stats, user=current_user, arrear_count=arrear_count)

@main_bp.route('/rankings')
@login_required
def rankings():
    db = get_db()
    years = ['First Year', 'Second Year', 'Third Year']
    rankings_data = {}
    for year in years:
        students = list(db.students.find({'year': year}, {
            'name': 1, 'rollno': 1, 'year': 1, 'semesters': 1
        }))
        ranked = []
        for s in students:
            cgpa = compute_cgpa(s.get('semesters', {}))
            arrears = get_arrears(s.get('semesters', {}))
            active_arrears = [a for a in arrears if not a['cleared']]
            ranked.append({
                '_id': str(s['_id']),
                'name': s.get('name'),
                'rollno': s.get('rollno'),
                'cgpa': cgpa,
                'arrear_count': len(active_arrears)
            })
        ranked = [r for r in ranked if r['cgpa'] is not None]
        ranked.sort(key=lambda x: x['cgpa'], reverse=True)
        rankings_data[year] = ranked[:10]
    return render_template('rankings.html', rankings_data=rankings_data)

@main_bp.route('/arrears')
@login_required
def arrears():
    db = get_db()
    year_filter = request.args.get('year', '')
    query = {'year': year_filter} if year_filter else {}
    students = list(db.students.find(query, {
        'name': 1, 'rollno': 1, 'year': 1, 'semesters': 1
    }))
    arrear_students = []
    for s in students:
        arrears_list = get_arrears(s.get('semesters', {}))
        if arrears_list:
            arrear_students.append({
                '_id': str(s['_id']),
                'name': s.get('name'),
                'rollno': s.get('rollno'),
                'year': s.get('year'),
                'arrears': arrears_list,
                'total_arrears': len(arrears_list),
                'cleared': sum(1 for a in arrears_list if a['cleared']),
                'pending': sum(1 for a in arrears_list if not a['cleared']),
            })
    arrear_students.sort(key=lambda x: x['pending'], reverse=True)
    year_counts = {
        'all': len(arrear_students),
        'First Year':  sum(1 for s in arrear_students if s['year'] == 'First Year'),
        'Second Year': sum(1 for s in arrear_students if s['year'] == 'Second Year'),
        'Third Year':  sum(1 for s in arrear_students if s['year'] == 'Third Year'),
    }
    return render_template('arrears.html', arrear_students=arrear_students,
                           year_filter=year_filter, year_counts=year_counts)

@main_bp.route('/arrears/toggle', methods=['POST'])
@login_required
def toggle_arrear():
    db = get_db()
    data = request.get_json()
    student_id = data.get('student_id')
    sem_key    = data.get('sem_key')
    subject    = data.get('subject')
    cleared    = data.get('cleared', False)
    student = db.students.find_one({'_id': ObjectId(student_id)})
    if not student:
        return jsonify({'success': False}), 404
    semesters = student.get('semesters', {})
    subjects  = semesters.get(sem_key, [])
    for subj in subjects:
        if subj.get('subject') == subject:
            subj['cleared'] = cleared
            break
    semesters[sem_key] = subjects
    db.students.update_one({'_id': ObjectId(student_id)}, {'$set': {'semesters': semesters}})
    return jsonify({'success': True})
