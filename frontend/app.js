const API_URL = `http://${window.location.hostname}:8000/api/v1`;

// Verificar sesión al cargar
document.addEventListener('DOMContentLoaded', () => {
    const username = localStorage.getItem('username');
    if(username) {
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
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        
        const data = await res.json();
        if(res.ok && data.status === 'success') {
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
        firstname: document.getElementById('reg-firstname').value,
        lastname: document.getElementById('reg-lastname').value,
        email: document.getElementById('reg-email').value,
        department: document.getElementById('reg-dept').value,
        password: document.getElementById('reg-pass').value
    };
    try {
        const res = await fetch(`${API_URL}/users`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            e.target.reset();
            showSuccess("Usuario creado exitosamente.");
            loadUsers();
        } else {
            let errorMsg = "Error al crear usuario";
            if (Array.isArray(data.detail)) {
                // Extraer mensajes de error de Pydantic y limpiarlos
                errorMsg = data.detail.map(e => e.msg.replace('Value error, ', '')).join('\n');
            } else if (data.detail) {
                errorMsg = data.detail;
            }
            showError(errorMsg);
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Crear usuario';
    }
}

async function handleDeleteUser(username) {
    try {
        const res = await fetch(`${API_URL}/users/${encodeURIComponent(username)}`, {
            method: 'DELETE',
            credentials: 'include'
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

function openRoleModal(username, currentRoles) {
    document.getElementById('modal-username').innerText = username;
    document.getElementById('modal-username').dataset.roles = currentRoles;
    
    const rolesArray = currentRoles ? currentRoles.split(',') : [];
    document.getElementById('role-admins').checked = rolesArray.includes('admins');
    document.getElementById('role-profesores').checked = rolesArray.includes('profesores');
    document.getElementById('role-estudiantes').checked = rolesArray.includes('estudiantes');

    document.getElementById('role-modal').classList.remove('hidden');
}

function closeRoleModal() {
    document.getElementById('role-modal').classList.add('hidden');
}

async function submitRoleChanges() {
    const username = document.getElementById('modal-username').innerText;
    const btn = document.getElementById('btn-save-roles');
    btn.disabled = true;
    btn.innerText = 'Guardando...';

    const rolesToManage = ['admins', 'profesores', 'estudiantes'];
    const selectedRoles = [];

    rolesToManage.forEach(role => {
        if (document.getElementById(`role-${role}`).checked) {
            selectedRoles.push(role);
        }
    });

    try {
        const res = await fetch(`${API_URL}/users/${encodeURIComponent(username)}/roles`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({roles: selectedRoles})
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || "Error al modificar los roles");
        }
        
        closeRoleModal();
        loadUsers();
    } catch (error) {
        showError(error.message || "Error de red al actualizar los roles");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Guardar';
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
    const currentUsername = localStorage.getItem('username');
    const admin = isAdmin();

    try {
        const res = await fetch(`${API_URL}/users`, {
            credentials: 'include',
            cache: 'no-store'
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
                    actionsCell = `
                        <td class="admin-only">
                            <button class="btn-action btn-success" onclick="openRoleModal('${user.username}', '${roles.join(',')}')">Editar Rol</button>
                            <button class="btn-action btn-danger" onclick="handleDeleteUser('${user.username}')" ${user.username === currentUsername ? 'disabled' : ''}>Borrar</button>
                        </td>`;
                }
                tr.innerHTML = `
                    <td><strong>${user.username}</strong></td>
                    <td>${user.firstname || '—'}</td>
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

async function logout() {
    try {
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch(e) { console.log(e); }
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

function showPasswordError(msg) {
    const errDiv = document.getElementById('password-error');
    errDiv.innerText = msg;
    errDiv.classList.remove('hidden');
    setTimeout(() => { errDiv.classList.add('hidden'); }, 5000);
}

function filterTable() {
    const input = document.getElementById("search-input").value.toLowerCase();
    const rows = document.getElementById("users-tbody").getElementsByTagName("tr");

    for (let i = 0; i < rows.length; i++) {
        let textContent = rows[i].innerText.toLowerCase();
        if (textContent.includes(input)) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}

function openPasswordModal() {
    document.getElementById('password-form').reset();
    document.getElementById('password-error').classList.add('hidden');
    document.getElementById('password-modal').classList.remove('hidden');
}

function closePasswordModal() {
    document.getElementById('password-modal').classList.add('hidden');
}

async function submitPasswordChange(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-password');
    btn.disabled = true;
    btn.innerText = 'Actualizando...';

    const old_password = document.getElementById('old-pass').value;
    const new_password = document.getElementById('new-pass').value;

    try {
        const res = await fetch(`${API_URL}/users/me/password`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ old_password, new_password })
        });

        const data = await res.json();
        if(res.ok) {
            closePasswordModal();
            showSuccess(data.message || "Contraseña actualizada exitosamente.");
            setTimeout(() => {
                logout(); // Obligamos al usuario a volver a iniciar sesión por seguridad
            }, 2000);
        } else {
            let errorMsg = "Error al actualizar la contraseña";
            if (Array.isArray(data.detail)) {
                errorMsg = data.detail.map(e => e.msg.replace('Value error, ', '')).join('\\n');
            } else if (data.detail) {
                errorMsg = data.detail;
            }
            showPasswordError(errorMsg);
        }
    } catch (error) {
        showPasswordError("Error de conexión con el servidor");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Actualizar';
    }
}

async function openAuditModal() {
    document.getElementById('audit-modal').classList.remove('hidden');
    const content = document.getElementById('audit-content');
    content.innerHTML = "Cargando logs...";
    try {
        const res = await fetch(`${API_URL}/audit/logs`, {
            credentials: 'include'
        });
        const data = await res.json();
        if(res.ok) {
            content.innerHTML = data.logs.join('<br>') || "No hay registros disponibles.";
        } else {
            content.innerHTML = "Error al cargar los logs. Asegúrate de tener permisos de Administrador.";
        }
    } catch(e) {
        content.innerHTML = "Error de conexión con el servidor.";
    }
}

function closeAuditModal() {
    document.getElementById('audit-modal').classList.add('hidden');
}
