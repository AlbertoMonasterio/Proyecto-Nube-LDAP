const API_URL = 'http://127.0.0.1:8000/api/v1';

// Verificar sesión al cargar
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    if(token && username) {
        showDashboard(username);
    }
});

async function handleLogin(e) {
    e.preventDefault();
    hideMessages();
    const btn = document.getElementById('btn-login');
    btn.disabled = true;
    btn.innerText = 'Verificando...';

    const u = document.getElementById('user').value;
    const p = document.getElementById('pass').value;

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        
        const data = await res.json();
        if(res.ok && data.status === 'success') {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', data.username);
            localStorage.setItem('roles', JSON.stringify(data.roles || []));
            showDashboard(data.username);
        } else {
            showError(data.detail || "Credenciales incorrectas");
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Ingresar';
    }
}

async function handleAdminCreateUser(e) {
    e.preventDefault();
    hideMessages();
    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.innerText = 'Creando...';

    const payload = {
        username: document.getElementById('reg-user').value,
        lastname: document.getElementById('reg-lastname').value,
        email: document.getElementById('reg-email').value,
        department: document.getElementById('reg-dept').value,
        password: document.getElementById('reg-pass').value
    };
    const token = localStorage.getItem('token');

    try {
        const res = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if(res.ok) {
            showSuccess("Usuario creado exitosamente.");
            e.target.reset();
            loadUsers();
        } else {
            showError(data.detail || "Error al crear el usuario");
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Crear usuario';
    }
}

async function handleDeleteUser(username) {
    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${API_URL}/users/${encodeURIComponent(username)}`, {
            method: 'DELETE',
            headers: {'Authorization': `Bearer ${token}`}
        });
        const data = await res.json();
        if(res.ok) {
            loadUsers();
        } else {
            showError(data.detail || "Error al eliminar el usuario");
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    }
}

async function handleRoleChange(username, role, action) {
    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${API_URL}/users/${encodeURIComponent(username)}/role`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({action, role})
        });
        const data = await res.json();
        if(res.ok) {
            loadUsers();
        } else {
            showError(data.detail || "Error al actualizar el rol");
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    }
}

function isAdmin() {
    const roles = JSON.parse(localStorage.getItem('roles') || '[]');
    return roles.includes('admins');
}

function showDashboard(username) {
    document.getElementById('auth-view').classList.add('hidden');
    const dashboard = document.getElementById('dashboard-view');
    dashboard.classList.remove('hidden');
    dashboard.classList.add('slide-up');
    document.getElementById('display-name').innerText = username;

    const admin = isAdmin();
    document.getElementById('admin-create-form').classList.toggle('hidden', !admin);
    document.querySelectorAll('.admin-only').forEach(el => el.classList.toggle('hidden', !admin));

    loadUsers();
}

async function loadUsers() {
    const tbody = document.getElementById('users-tbody');
    const loader = document.getElementById('loading-users');
    const token = localStorage.getItem('token');
    const currentUsername = localStorage.getItem('username');
    const admin = isAdmin();

    try {
        const res = await fetch(`${API_URL}/users`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if(res.status === 401) {
            logout(); // Token expirado
            return;
        }

        const data = await res.json();
        if(res.ok) {
            loader.classList.add('hidden');
            tbody.innerHTML = '';

            data.users.forEach(user => {
                const roles = user.roles || [];
                const tr = document.createElement('tr');
                let actionsCell = '';
                if(admin) {
                    const roleOptions = ['admins', 'profesores', 'estudiantes']
                        .map(r => `<option value="${r}">${r}</option>`).join('');
                    actionsCell = `
                        <td class="admin-only">
                            <select data-user="${user.username}" class="role-select">${roleOptions}</select>
                            <button onclick="handleRoleChange('${user.username}', this.parentElement.querySelector('select').value, 'add')">Asignar</button>
                            <button onclick="handleRoleChange('${user.username}', this.parentElement.querySelector('select').value, 'remove')">Quitar</button>
                            <button onclick="handleDeleteUser('${user.username}')" ${user.username === currentUsername ? 'disabled' : ''}>Borrar</button>
                        </td>`;
                }
                tr.innerHTML = `
                    <td><strong>${user.username}</strong></td>
                    <td>${user.lastname}</td>
                    <td><span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem">${user.department}</span></td>
                    <td>${user.email}</td>
                    <td>${roles.join(', ') || '—'}</td>
                    ${actionsCell}
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (error) {
        loader.innerText = "Error cargando directorio";
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('roles');
    location.reload();
}

function showError(msg) {
    const el = document.getElementById('error-msg');
    el.innerText = msg;
    el.classList.remove('hidden');
}

function showSuccess(msg) {
    const el = document.getElementById('success-msg');
    el.innerText = msg;
    el.classList.remove('hidden');
}

function hideMessages() {
    document.getElementById('error-msg').classList.add('hidden');
    document.getElementById('success-msg').classList.add('hidden');
}
