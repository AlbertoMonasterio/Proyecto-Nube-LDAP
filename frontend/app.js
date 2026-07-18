const API_URL = 'http://127.0.0.1:8000/api/v1';

// Verificar sesión al cargar
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    if(token && username) {
        showDashboard(username);
    }
});

function toggleAuthForm(type) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    hideMessages();

    if(type === 'register') {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        registerForm.classList.add('slide-up');
    } else {
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        loginForm.classList.add('slide-up');
    }
}

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

async function handleRegister(e) {
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

    try {
        const res = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if(res.ok) {
            showSuccess("Cuenta creada exitosamente. Ya puedes iniciar sesión.");
            setTimeout(() => toggleAuthForm('login'), 2000);
        } else {
            showError(data.detail || "Error al registrar el usuario");
        }
    } catch (error) {
        showError("Error de conexión con el servidor");
    } finally {
        btn.disabled = false;
        btn.innerText = 'Crear Cuenta';
    }
}

function showDashboard(username) {
    document.getElementById('auth-view').classList.add('hidden');
    const dashboard = document.getElementById('dashboard-view');
    dashboard.classList.remove('hidden');
    dashboard.classList.add('slide-up');
    document.getElementById('display-name').innerText = username;
    
    loadUsers();
}

async function loadUsers() {
    const tbody = document.getElementById('users-tbody');
    const loader = document.getElementById('loading-users');
    const token = localStorage.getItem('token');
    
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
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${user.username}</strong></td>
                    <td>${user.lastname}</td>
                    <td><span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem">${user.department}</span></td>
                    <td>${user.email}</td>
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
