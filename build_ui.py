from pathlib import Path

def main():
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)

    html_content = """<!DOCTYPE html>
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
    </style>
</head>
<body>

    <div id="login-screen">
        <div class="login-box">
            <h2>School Login</h2>
            <div id="login-error" style="color: red; margin-bottom: 1rem; display: none;"></div>
            <input type="email" id="email" placeholder="Email" value="admin@school.test">
            <input type="password" id="password" placeholder="Password" value="AdminPass123">
            <button onclick="login()">Sign In</button>
        </div>
    </div>

    <div id="dashboard">
        <div class="sidebar">
            <h2>SMS Dashboard</h2>
            <div class="nav-item active" onclick="switchTab('students', this)">Students</div>
            <div class="nav-item" onclick="switchTab('teachers', this)">Teachers</div>
            <div class="nav-item" onclick="switchTab('announcements', this)">Announcements</div>
            <div style="margin-top: auto;">
                <div class="nav-item" onclick="logout()" style="color: #ef4444;">Logout</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1 id="page-title">Students Directory</h1>
                <div id="user-info" style="font-weight: 600;"></div>
            </div>

            <div id="tab-students">
                <div class="card">
                    <h3>Add New Student</h3>
                    <div class="form-row">
                        <input type="text" id="s-adm" placeholder="Admission No">
                        <input type="text" id="s-first" placeholder="First Name">
                        <input type="text" id="s-last" placeholder="Last Name">
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

            <div id="tab-teachers" class="hidden">
                <div class="card">
                    <h3>All Teachers</h3>
                    <table>
                        <thead><tr><th>ID</th><th>Employee No</th><th>Name</th><th>Phone</th></tr></thead>
                        <tbody id="teachers-table"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-announcements" class="hidden">
                <div class="card">
                    <h3>School Announcements</h3>
                    <div id="announcements-list" style="margin-top: 1rem;"></div>
                </div>
            </div>

        </div>
    </div>

    <script>
        let token = localStorage.getItem('token');
        if (token) showDashboard();

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
                showDashboard();
            } catch (err) {
                errorDiv.innerText = err.message;
                errorDiv.style.display = 'block';
            }
        }

        function logout() {
            localStorage.removeItem('token');
            token = null;
            location.reload();
        }

        async function apiFetch(endpoint, options = {}) {
            options.headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
            const res = await fetch(endpoint, options);
            if (res.status === 401) logout();
            return res;
        }

        function showDashboard() {
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('dashboard').style.display = 'flex';
            apiFetch('/auth/me').then(res => res.json()).then(user => {
                document.getElementById('user-info').innerText = `${user.full_name} (${user.role})`;
            });
            loadStudents();
        }

        function switchTab(tabName, el) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');
            document.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.add('hidden'));
            document.getElementById(`tab-${tabName}`).classList.remove('hidden');
            document.getElementById('page-title').innerText = tabName.charAt(0).toUpperCase() + tabName.slice(1);
            
            if (tabName === 'students') loadStudents();
            if (tabName === 'teachers') loadTeachers();
            if (tabName === 'announcements') loadAnnouncements();
        }

        async function loadStudents() {
            const res = await apiFetch('/students');
            const students = await res.json();
            const tbody = document.getElementById('students-table');
            tbody.innerHTML = students.map(s => `
                <tr>
                    <td>${s.id}</td>
                    <td>${s.admission_no}</td>
                    <td>${s.first_name} ${s.last_name}</td>
                    <td>${s.gender || '-'}</td>
                </tr>
            `).join('');
        }

        async function addStudent() {
            const data = {
                admission_no: document.getElementById('s-adm').value,
                first_name: document.getElementById('s-first').value,
                last_name: document.getElementById('s-last').value
            };
            if (!data.admission_no || !data.first_name || !data.last_name) return alert('Fill all fields');

            await apiFetch('/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            document.getElementById('s-adm').value = '';
            document.getElementById('s-first').value = '';
            document.getElementById('s-last').value = '';
            loadStudents();
        }

        async function loadTeachers() {
            const res = await apiFetch('/teachers');
            const teachers = await res.json();
            const tbody = document.getElementById('teachers-table');
            tbody.innerHTML = teachers.map(t => `
                <tr>
                    <td>${t.id}</td>
                    <td>${t.employee_no}</td>
                    <td>${t.first_name} ${t.last_name}</td>
                    <td>${t.phone || '-'}</td>
                </tr>
            `).join('');
        }

        async function loadAnnouncements() {
            const res = await apiFetch('/announcements');
            const anns = await res.json();
            const list = document.getElementById('announcements-list');
            if (anns.length === 0) return list.innerHTML = '<p>No announcements yet.</p>';
            
            list.innerHTML = anns.map(a => `
                <div style="border-left: 4px solid var(--primary); padding: 1rem; background: #f8fafc; margin-bottom: 1rem;">
                    <h4 style="margin-bottom: 0.5rem;">${a.title}</h4>
                    <p>${a.body}</p>
                    <small style="color: gray;">Audience: ${a.audience}</small>
                </div>
            `).join('');
        }
    </script>
</body>
</html>"""
    
    static_dir.joinpath("index.html").write_text(html_content, encoding="utf-8")
    print("Created static/index.html")

    main_py = Path("app/main.py")
    text = main_py.read_text(encoding="utf-8")
    
    if "StaticFiles" not in text:
        text = text.replace(
            "from fastapi.middleware.cors import CORSMiddleware",
            "from fastapi.middleware.cors import CORSMiddleware\nfrom fastapi.staticfiles import StaticFiles"
        )
        text += '\n\napp.mount("/ui", StaticFiles(directory="static", html=True), name="static")\n'
        main_py.write_text(text, encoding="utf-8")
        print("Patched app/main.py")

    print("\nDone. Restart your server and go to http://127.0.0.1:8000/ui")

if __name__ == "__main__":
    main()
