import pathlib

# 1. Force-fix schemas.py to drop EmailStr and the bad import
schemas_path = pathlib.Path("app/schemas.py")
text = schemas_path.read_text(encoding="utf-8")
text = text.replace("from pydantic import BaseModel, ConfigDict, EmailStr, Field", "from pydantic import BaseModel, ConfigDict, Field")
text = text.replace("email: EmailStr", "email: str")
schemas_path.write_text(text, encoding="utf-8")
print("Fixed app/schemas.py")

# 2. Force-fix the frontend to show real errors
html_path = pathlib.Path("static/index.html")
html = html_path.read_text(encoding="utf-8")

old_js = """            const res = await apiFetch('/students', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
            });
            if (!res.ok) return alert('Error adding student (check email uniqueness)');
            
            loadStudents();"""

new_js = """            const res = await apiFetch('/students', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
            });
            
            if (!res.ok) {
                const errorData = await res.json();
                let msg = "Error adding student";
                if (Array.isArray(errorData.detail)) {
                    msg = errorData.detail.map(e => e.msg).join(', ');
                } else if (typeof errorData.detail === 'string') {
                    msg = errorData.detail;
                }
                return alert("BACKEND ERROR: " + msg);
            }
            
            document.getElementById('s-adm').value = '';
            document.getElementById('s-first').value = '';
            document.getElementById('s-last').value = '';
            document.getElementById('s-email').value = '';
            document.getElementById('s-pass').value = '';
            
            loadStudents();"""

if old_js in html:
    html = html.replace(old_js, new_js)
    html_path.write_text(html, encoding="utf-8")
    print("Fixed static/index.html")
else:
    print("Could not find the old JS to replace. Did you modify index.html?")
