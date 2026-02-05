# 🚀 Configuración de Deploy Automático

## Paso 1: Generar SSH Key para GitHub Actions

En tu **VPS**, ejecuta:

```bash
# Generar nueva SSH key (sin passphrase para automatización)
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_key -N ""

# Ver la clave privada (la necesitarás para GitHub)
cat ~/.ssh/github_actions_key

# Agregar clave pública a authorized_keys
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys

# Permisos correctos
chmod 600 ~/.ssh/github_actions_key
chmod 644 ~/.ssh/github_actions_key.pub
```

## Paso 2: Configurar Secrets en GitHub

1. Ve a tu repositorio en GitHub: `https://github.com/claudioqy5/ni-os-aly`
2. Click en **Settings** (pestaña superior)
3. Click en **Secrets and variables** → **Actions**
4. Click en **New repository secret**
5. Crea estos 3 secrets:

### Secret 1: VPS_HOST
- **Name:** `VPS_HOST`
- **Value:** La IP de tu VPS (ejemplo: `123.45.67.89`)

### Secret 2: VPS_USER
- **Name:** `VPS_USER`
- **Value:** Tu usuario del VPS (ejemplo: `root` o `ubuntu`)

### Secret 3: VPS_SSH_KEY
- **Name:** `VPS_SSH_KEY`
- **Value:** El contenido completo de `~/.ssh/github_actions_key` (la clave privada)

## Paso 3: Ajustar el Workflow

En el archivo `.github/workflows/deploy.yml`, actualiza:

1. **Ruta del proyecto:** Cambia `/ruta/a/tu/proyecto/niños-aly` por la ruta real
2. **Nombres de servicios:** Cambia `ninos-aly-backend` y `ninos-aly-frontend` por los nombres reales de tus servicios

### ¿No sabes los nombres de tus servicios?

En el VPS, ejecuta:
```bash
# Ver servicios activos
sudo systemctl list-units --type=service | grep -i ninos
# o
sudo systemctl list-units --type=service | grep -i python
sudo systemctl list-units --type=service | grep -i node
```

## Paso 4: Dar Permisos Sudo sin Password (Opcional pero Recomendado)

Para que GitHub Actions pueda reiniciar servicios automáticamente:

En el **VPS**, ejecuta:
```bash
# Editar sudoers
sudo visudo

# Agregar al final (reemplaza 'tu_usuario' con tu usuario real):
tu_usuario ALL=(ALL) NOPASSWD: /bin/systemctl restart ninos-aly-backend
tu_usuario ALL=(ALL) NOPASSWD: /bin/systemctl restart ninos-aly-frontend
tu_usuario ALL=(ALL) NOPASSWD: /bin/systemctl status ninos-aly-backend
tu_usuario ALL=(ALL) NOPASSWD: /bin/systemctl status ninos-aly-frontend
```

## Paso 5: Hacer Commit del Workflow

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add automatic deployment workflow"
git push origin main
```

## Paso 6: Verificar el Deploy

1. Ve a tu repositorio en GitHub
2. Click en la pestaña **Actions**
3. Deberías ver el workflow ejecutándose
4. Click en el workflow para ver los logs en tiempo real

---

## 🎯 ¿Cómo Funciona?

Ahora, **cada vez que hagas `git push origin main`**:

1. ✅ GitHub detecta el push
2. ✅ Ejecuta el workflow automáticamente
3. ✅ Se conecta a tu VPS por SSH
4. ✅ Hace `git pull` en el VPS
5. ✅ Instala dependencias
6. ✅ Reinicia los servicios
7. ✅ Tu aplicación se actualiza automáticamente

**No necesitas hacer SSH manual nunca más!** 🎉

---

## 🔧 Troubleshooting

### Error: "Permission denied (publickey)"
- Verifica que copiaste la clave privada correcta en `VPS_SSH_KEY`
- Verifica que la clave pública esté en `~/.ssh/authorized_keys` del VPS

### Error: "sudo: no tty present"
- Necesitas configurar sudoers como se indica en el Paso 4

### El workflow no se ejecuta
- Verifica que el archivo esté en `.github/workflows/deploy.yml`
- Verifica que el branch sea `main` (no `master`)

### Ver logs del deployment
- En GitHub → Actions → Click en el workflow más reciente
