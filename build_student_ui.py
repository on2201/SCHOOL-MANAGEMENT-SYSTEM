from pathlib import Path

def main():
    # 1. Patch models.py to easily expose student_id
    p = Path("app/models.py")
    text = p.read_text(encoding="utf-8")
    if "def student_id(self) -> int | None:" not in text:
        text = text.replace(
            "    teacher: Mapped[Teacher | None] = relationship(back_populates=\"user\", uselist=False)\n    guardian: Mapped[Guardian | None] = relationship(back_populates=\"user\", uselist=False)",
            "    teacher: Mapped[Teacher | None] = relationship(back_populates=\"user\", uselist=False)\n    guardian: Mapped[Guardian | None] = relationship(back_populates=\"user\", uselist=False)\n\n    @property\n    def student_id(self) -> int | None:\n        return self.student.id if self.student else None"
        )
        p.write_text(text, encoding="utf-8")
        print("Patched models.py")

    # 2. Patch schemas.py to return student_id
    p = Path("app/schemas.py")
    text = p.read_text(encoding="utf-8")
    if "student_id: int | None" not in text:
        text = text.replace(
            "class UserOut(ORMModel):\n    id: int\n    email: EmailStr\n    full_name: str\n    role: Role\n    is_active: bool",
            "class UserOut(ORMModel):\n    id: int\n    email: EmailStr\n    full_name: str\n    role: Role\n    is_active: bool\n    student_id: int | None = None"
        )
        p.write_text(text, encoding="utf-8")
        print("Patched schemas.py")

    # 3. Overwrite static/index.html with the Role-Based UI
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>School Management System</title>
    <style>
        :root { --primary: #2563eb; --bg: #f3f4f6; --surface: #ffffff; --text: #1f2937; --border: #e5e7eb; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; }
        
        #login-screen { display: flex; height: 100vh; align-items: center; justify-content: center; }
        .login-box { background: var(--surface); padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); width: 100%; max-width: 400px; }
        .login-box h2 { margin-bottom: 1.5rem; text-align: center; }
        input { width: 100%; padding: 0.75rem; margin-bottom: 1rem; border: 1px solid var(--border); border-radius: 4px; }
        button { width: 100%; padding: 0.75rem; background: var(--primary); color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
        button:hover { background: #1d4ed8; }
        
        #dashboard { display: none; height: 100vh; }
        .sidebar { width: 250px; background: #111827; color: white; padding: 1rem; display: flex; flex-direction: column; }
        .sidebar h2 { font-size: 1.25rem; margin-bottom: 2rem; text-align: center; }
        .nav-item { padding: 0.75rem; cursor: pointer; border-radius: 4px; margin-bottom: 0.5rem; }
        .nav-item:hover, .nav-item.active { background: #374151; }
        
        .main-content { flex: 1; padding: 2rem; overflow-y: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .card { background: var(--surface); border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgb(0 0 0 / 0.1); margin-bottom: 2rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: #f9fafb; font-weight: 600; }
        
        .form-row { display: flex; gap: 1rem; margin-bottom: 1rem; }
        .form-row input { margin-bottom: 0; }
        .form-row button { width: auto; padding: 0.75rem 1.5rem; }
        
        .hidden { display: none !important; }
        .stat-box { display: flex; gap: 1rem; margin-bottom: 1rem; }
        .stat { background: #e0e7ff; padding: 1rem; border-radius: 8px; flex: 1; text-align: center; }
        .stat h4 { font-size: 2rem; color: var(--primary); }
    </style>
</head>
<body>

    <div id="login-screen">
        <div class="login-box">
            <h2>School Login</h2>
            <div id="login-error" style="color: red; margin-bottom: 1rem; display: none;"></div>
            <input type="email" id="email" placeholder="Email" value="student1@school.test">
            <input type="password" id="password" placeholder="Password" value="StudentPass123">
            <button onclick="login()">Sign In</button>
            <p style="text-align: center; margin-top: 1rem; font-size: 0.875rem; color: gray;">Try Admin: admin@school.test / AdminPass123</p>
        </div>
    </div>

    <div id="dashboard">
        <div class="sidebar">
            <h2>SMS Dashboard</h2>
            
            <div id="menu-admin" class="hidden">
                <div class="nav-item active" onclick="switchTab('admin-students', this)">Manage Students</div>
                <div class="nav-item" onclick="switchTab('admin-teachers', this)">Manage Teachers</div>
            </div>

            <div id="menu-student" class="hidden">
                <div class="nav-item active" onclick="switchTab('student-grades', this)">My Grades</div>
                <div class="nav-item" onclick="switchTab('student-attendance', this)">My Attendance</div>
            </div>

            <div style="margin-top: auto;">
                <div class="nav-item" onclick="logout()" style="color: #ef4444;">Logout</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1 id="page-title">Dashboard</h1>
                <div id="user-info" style="font-weight: 600;"></div>
            </div>

            <div id="tab-admin-students" class="hidden">
                <div class="card">
                    <h3>Add New Student</h3>
                    <div class="form-row">
                        <input type="text" id="s-adm" placeholder="Admission No">
                        <input type="text" id="s-first" placeholder="First Name">
                        <input type="text" id="s-last" placeholder="Last Name">
                        <input type="email" id="s-email" placeholder="Email">
                        <input type="password" id="s-pass" placeholder="Password">
                        <button onclick="addStudent()">Add Student</button>
                    </div>
                </div>
                <div class="card">
                    <h3>All Students</h3>
                    <table>
                        <thead><tr><th>ID</th><th>Admission No</th><th>Name</th><th>Gender</th></tr></thead>
                        <tbody id="students-table"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-admin-teachers" class="hidden">
                <div class="card">
                    <h3>All Teachers</h3>
                    <table>
                        <thead><tr><th>ID</th><th>Employee No</th><th>Name</th><th>Phone</th></tr></thead>
                        <tbody id="teachers-table"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-student-grades" class="hidden">
                <div class="card">
                    <h3>My Report Card</h3>
                    <div id="report-card" style="margin-top: 1rem;"></div>
                </div>
            </div>

            <div id="tab-student-attendance" class="hidden">
                <div class="card">
                    <h3>My Attendance Summary</h3>
                    <div id="attendance-summary" style="margin-top: 1rem;"></div>
                </div>
                <div class="card">
                    <h3>Recent Records</h3>
                    <table>
                        <thead><tr><th>Date</th><th>Status</th><th>Note</th></tr></thead>
                        <tbody id="attendance-table"></tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>

    <script>
        let token = localStorage.getItem('token');
        let currentUser = null;

        if (token) loadUser();

        async function login() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('login-error');
            errorDiv.style.display = 'none';
            
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            try {
                const res = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });
                if (!res.ok) throw new Error('Invalid credentials');
                const data = await res.json();
                token = data.access_token;
                localStorage.setItem('token', token);
                loadUser();
            } catch (err) {
                errorDiv.innerText = err.message;
                errorDiv.style.display = 'block';
            }
        }

        function logout() {
            localStorage.removeItem('token');
            token = null;
            currentUser = null;
            location.reload();
        }

        async function apiFetch(endpoint, options = {}) {
            options.headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
            const res = await fetch(endpoint, options);
            if (res.status === 401) logout();
            return res;
        }

        async function loadUser() {
            const res = await apiFetch('/auth/me');
            if (!res.ok) return logout();
            currentUser = await res.json();
            
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('dashboard').style.display = 'flex';
            document.getElementById('user-info').innerText = `${currentUser.full_name} (${currentUser.role})`;

            if (currentUser.role === 'admin') {
                document.getElementById('menu-admin').classList.remove('hidden');
                switchTab('admin-students', document.querySelector('#menu-admin .nav-item'));
            } else if (currentUser.role === 'student') {
                document.getElementById('menu-student').classList.remove('hidden');
                switchTab('student-grades', document.querySelector('#menu-student .nav-item'));
            } else {
                document.getElementById('page-title').innerText = "Dashboard";
                document.querySelector('.main-content').innerHTML = "<h2>Teacher portal not built yet.</h2>";
            }
        }

        function switchTab(tabName, el) {
            if (el) {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                el.classList.add('active');
            }
            document.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.add('hidden'));
            document.getElementById(`tab-${tabName}`).classList.remove('hidden');
            
            document.getElementById('page-title').innerText = el ? el.innerText : "Dashboard";
            
            if (tabName === 'admin-students') loadStudents();
            if (tabName === 'admin-teachers') loadTeachers();
            if (tabName === 'student-grades') loadGrades();
            if (tabName === 'student-attendance') loadAttendance();
        }

        async function loadStudents() {
            const res = await apiFetch('/students');
            const students = await res.json();
            document.getElementById('students-table').innerHTML = students.map(s => `
                <tr><td>${s.id}</td><td>${s.admission_no}</td><td>${s.first_name} ${s.last_name}</td><td>${s.gender || '-'}</td></tr>
            `).join('');
        }

        async function addStudent() {
            const data = {
                admission_no: document.getElementById('s-adm').value,
                first_name: document.getElementById('s-first').value,
                last_name: document.getElementById('s-last').value,
                email: document.getElementById('s-email').value,
                password: document.getElementById('s-pass').value
            };
            if (!data.admission_no || !data.first_name || !data.last_name) return alert('Fill required fields');

            const res = await apiFetch('/students', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
            });
            if (!res.ok) return alert('Error adding student (check email uniqueness)');
            
            loadStudents();
        }

        async function loadTeachers() {
            const res = await apiFetch('/teachers');
            const teachers = await res.json();
            document.getElementById('teachers-table').innerHTML = teachers.map(t => `
                <tr><td>${t.id}</td><td>${t.employee_no}</td><td>${t.first_name} ${t.last_name}</td><td>${t.phone || '-'}</td></tr>
            `).join('');
        }

        async function loadGrades() {
            const res = await apiFetch(`/assessments/students/${currentUser.student_id}/report?term_id=1`);
            if (!res.ok) {
                document.getElementById('report-card').innerHTML = '<p>No grades found yet, or term 1 does not exist.</p>';
                return;
            }
            const data = await res.json();
            
            let html = `<h4>Overall Percentage: ${data.overall_percentage}%</h4><br>`;
            data.subjects.forEach(sub => {
                html += `<div style="border-left: 4px solid var(--primary); padding: 1rem; background: #f8fafc; margin-bottom: 1rem;">
                    <h4>${sub.subject_name} (${sub.percentage.toFixed(1)}%)</h4>
                    <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">`;
                sub.lines.forEach(line => {
                    html += `<li>${line.title} (${line.type}): <b>${line.score || 'N/A'}</b> / ${line.max_score}</li>`;
                });
                html += `</ul></div>`;
            });
            document.getElementById('report-card').innerHTML = html;
        }

        async function loadAttendance() {
            const res = await apiFetch(`/attendance/student/${currentUser.student_id}/summary`);
            const summary = await res.json();
            
            let html = `<div class="stat-box">
                <div class="stat"><h4>${summary.attendance_rate}%</h4><p>Attendance Rate</p></div>
                <div class="stat"><h4>${summary.total_days}</h4><p>Total Days</p></div>
                <div class="stat"><h4 style="color: #ef4444">${summary.counts.absent || 0}</h4><p>Absences</p></div>
            </div>`;
            document.getElementById('attendance-summary').innerHTML = html;

            const recordsRes = await apiFetch(`/attendance/student/${currentUser.student_id}`);
            const records = await recordsRes.json();
            document.getElementById('attendance-table').innerHTML = records.map(r => `
                <tr><td>${r.date}</td><td>${r.status}</td><td>${r.note || '-'}</td></tr>
            `).join('');
        }
    </script>
</body>
</html>"""
    
    static_dir.joinpath("index.html").write_text(html_content, encoding="utf-8")
    print("Overwrote static/index.html with Role-Based UI")

if __name__ == "__main__":
    main()
