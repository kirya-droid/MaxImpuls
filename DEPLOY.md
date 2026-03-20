# 🚀 Настройка CI/CD

## 1. Создание SSH ключа для GitHub Actions

```bash
# Локально (Windows PowerShell от администратора)
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

**Не вводите пароль** (нажимайте Enter)

## 2. Копирование публичного ключа на сервер

```bash
# Копируем публичный ключ на сервер
type C:\Users\Кирюша\.ssh\github_actions.pub | ssh root@vm3591453 "cat >> /root/.ssh/authorized_keys"
```

Или вручную:
1. Откройте `C:\Users\Кирюша\.ssh\github_actions.pub`
2. Скопируйте содержимое
3. На сервере: `nano /root/.ssh/authorized_keys`
4. Вставьте ключ в конец файла
5. `Ctrl+O, Enter, Ctrl+X`

## 3. Добавление секретов в GitHub

1. Зайдите в репозиторий на GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**

Добавьте 3 секрета:

| Название | Значение |
|----------|----------|
| `SSH_PRIVATE_KEY` | Содержимое `~/.ssh/github_actions` (приватный ключ) |
| `SERVER_HOST` | `vm3591453` |
| `SERVER_USER` | `ImpulsBot` |

### Как получить приватный ключ:

```bash
# Windows PowerShell
Get-Content C:\Users\Кирюша\.ssh\github_actions | Set-Clipboard
```

Вставьте в GitHub (всё содержимое, включая `-----BEGIN...` и `-----END...`)

## 4. Инициализация Git репозитория

```bash
cd C:\Users\Кирюша\PycharmProjects\MaxImpulse

# Инициализация
git init

# Добавление файлов
git add .

# Первый коммит
git commit -m "Initial commit"

# Добавление remote (замените на ваш репозиторий)
git remote add origin https://github.com/YOUR_USERNAME/MaxImpulse.git

# Пуш в main
git branch -M main
git push -u origin main
```

## 5. Проверка деплоя

После пуша:
1. Зайдите на GitHub в репозиторий
2. **Actions** → увидите запущенный workflow
3. Через 1-2 минуты деплой завершится

## 6. Проверка на сервере

```bash
# Логи сервиса
journalctl -u tk_scanner -f

# Статус
systemctl status tk_scanner

# Логи бота
tail -f /home/ImpulsBot/tk_pro.log
```

---

## 🎯 Теперь при каждом `git push` в ветку `main`:

1. ✅ Код автоматически копируется на сервер
2. ✅ `pip install -r requirements.txt`
3. ✅ Сервис перезапускается
4. ✅ Вы получаете актуальные логи

## 📝 Использование

```bash
# Внесли изменения
git add .
git commit -m "Описание изменений"
git push

# Через 1-2 минуты изменения на сервере!
```

---

## 🔧 Ручной запуск деплоя

В GitHub: **Actions** → **🚀 Deploy to Server** → **Run workflow**
