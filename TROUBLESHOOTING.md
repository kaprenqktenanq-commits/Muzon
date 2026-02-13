# 🔧 Быстрая Справка по Исправлению Ошибок

## Если боту всё ещё плохо...

### 🔴 Ошибка: "Unknown Constructor 0x52d6806b"

**Причина:** Pyrogram версия старая или TL-схема не совпадает

**Решение:**
```bash
pip install pyrogram==2.0.106 --upgrade
# или
pip install -r requirements.txt --upgrade
```

**Если не помогло:**
```bash
# Очистить кэш
rm -rf ~/.pyrogram
# или если на Windows
rmdir /s %APPDATA%\pyrogram

# Переаутентифицировать
python -c "from pyrogram import Client; Client('bot').run()"
```

---

### 🔴 Ошибка: "All 10 external services failed"

**Причина:** yt-dlp не может загружать музыку, YouTube блокирует запросы

**Решение:**
```bash
# Обновить yt-dlp
pip install yt-dlp --upgrade

# Очистить кэш yt-dlp
rm -rf ~/.yt-dlp  # Linux/Mac
rmdir %APPDATA%\yt-dlp  # Windows
```

**Если всё ещё не работает:**
- Это временная проблема с YouTube или external API
- Бот автоматически пытается следующий способ
- Кликните play еще раз

---

### 🔴 Ошибка: "MongoDB connection failed"

**Причина:** Database не доступна

**Решение:**

1. **Проверить что MongoDB запущена:**
   ```bash
   # Если на localhost
   mongosh
   
   # Если на Atlas (cloud)
   # Проверить connection string в config.py
   ```

2. **Проверить connection string:**
   ```python
   # config.py должно иметь:
   DB_URI = "mongodb://user:pass@host:port/db"
   ```

3. **Проверить сетевой доступ:**
   ```bash
   ping mongo.example.com  # Если remote server
   ```

---

### 🔴 Ошибка: "TelegramServerError"

**Причина:** Telegram servers отвечают ошибкой (транзиентно)

**Решение:**
- ✅ Бот автоматически восстановится
- Это НЕ критично
- Просто смотрите логи, бот будет работать

```
[WARNING] TelegramServerError (transient): ...
[INFO] Reconnecting in 5s...
```

---

### 🟡 Ошибка: "No active group call"

**Причина:** Voice chat не включен в log channel

**Решение:**
1. Откройте log channel/group
2. Settings → Voice Chat Settings → Enable
3. Перезагрузите бот

---

### 🟡 Ошибка: "Assistant account X failed to access log group"

**Причина:** Юзербот не добавлен в log group или не админ

**Решение:**
1. Добавить юзербот в log group
2. Сделать его админ
3. Перезагрузить бот

---

### 🟡 Ошибка: "Assistant has no username"

**Причина:** Юзербот аккаунт без username

**Решение:**
1. Войти в юзербот аккаунт через Telegram
2. Settings → Username → Set username
3. Перезагрузить бот

---

### 🔴 Критичная Ошибка: "Max reconnection attempts reached"

**Причина:** После 5 попыток переподключения бот так и не запустился

**Это означает:**
- Серьезная проблема (не транзиентная)
- Нужно ручное вмешательство

**Что проверить:**
```bash
# 1. Проверить конфиг
python health_check.py

# 2. Проверить логи для ERROR
# (должна быть информация о реальной ошибке перед "Max reconnection")

# 3. Исправить проблему (обычно config, database, или credentials)

# 4. Перезагрузить
python -m ArmedMusic
```

---

## 📊 Уровни логирования

| Уровень | Примеры | Действие |
|---------|---------|----------|
| **DEBUG** | Пытаюсь загружать... | Игнорировать |
| **INFO** | ✓ Бот запущен | Нормально |
| **WARNING** | Unknown constructor, server error | Нормально, бот восстановится |
| **ERROR** | Module failed to load | Проверить конфиг |
| **CRITICAL** | Max reconnection attempts | Ручное вмешательство требуется |

---

## 🔍 Как читать логи

### На Render
Dashboard → Logs → поищите последние ERROR или CRITICAL

### На Docker
```bash
docker logs armedmusic | grep ERROR
docker logs armedmusic | tail -50
```

### На systemd
```bash
sudo journalctl -u armedmusic -n 50  # Последние 50 строк
sudo journalctl -u armedmusic -f  # В реальном времени
sudo journalctl -u armedmusic --grep ERROR  # Только ERROR
```

### Локально
Логи выводятся прямо в консоль (stdout)

---

## 🚀 Быстрые Команды

```bash
# Проверить всё перед запуском
python health_check.py

# Посмотреть Pyrogram версию
python -c "import pyrogram; print(pyrogram.__version__)"

# Посмотреть PyTgCalls версию
python -c "import pytgcalls; print(pytgcalls.__version__)"

# Перезагрузить бот с полной переинициализацией
pip install -r requirements.txt --upgrade
python -m ArmedMusic

# На Render: перезагрузить deployment
# В Render Dashboard: Deploy → Click "Deploy"

# На Docker: перезагрузить контейнер
docker restart armedmusic

# На systemd
sudo systemctl restart armedmusic
```

---

## 📝 Шаблон Issue Report

Если что-то не работает, проверьте:

```markdown
1. **Версия Pyrogram:** `python -c "import pyrogram; print(pyrogram.__version__)"`
2. **Версия Python:** `python --version`
3. **Версия PyTgCalls:** `python -c "import pytgcalls; print(pytgcalls.__version__)"`
4. **health_check результаты:** (copy-paste вывода)
5. **Логи ошибки:** (copy-paste последние 20 строк с ERROR/WARNING)
6. **Когда начало происходить:** (после обновления? после перезагрузки?)
```

---

## ✅ Успешный Запуск Выглядит Так

```
ArmedMusic.core.mongo - Connecting to MongoDB database...
ArmedMusic.core.mongo - Using database: armedmusic
ArmedMusic.core.mongo - ✓ MongoDB ping successful
ArmedMusic.core.mongo - ✓ Authentication successful
ArmedMusic.core.mongo - ✓ MongoDB async client created successfully
ArmedMusic.core.mongo - MongoDB connection initialized successfully
ArmedMusic.core.dir - Directories Updated.
ArmedMusic.misc - Local Database Initialized.
ArmedMusic.core.bot - Starting Bot...
ArmedMusic.misc - Sudoers Loaded.
ArmedMusic.core.bot - Bot commands configured successfully
ArmedMusic.core.bot - Music Bot Started as 𝑨𝒓𝒎𝒆𝒅 𝑴𝒖𝒛𝒊𝒄 
ArmedMusic.plugins - Successfully Imported Modules...
ArmedMusic.core.userbot - Starting Assistants...
ArmedMusic.core.userbot - Assistant Started as @username
ArmedMusic.core.call - ✓ PyTgCalls started successfully
ArmedMusic - ✓ All systems initialized successfully!
```

**Если видите это - ВСЕ РАБОТАЕТ! ✅**

---

## 🆘 Если НИЧЕГО не помогает

1. **Полная переинициализация:**
   ```bash
   # Очистить все кэши
   rm -rf ~/.pyrogram ~/.yt-dlp ~/.cache/pip ~/.cache/python
   
   # Переустановить зависимости чистой установкой
   pip uninstall pyrogram pytgcalls -y
   pip install -r requirements.txt
   
   # Запустить health_check
   python health_check.py
   
   # Запустить бот
   python -m ArmedMusic
   ```

2. **На Render - полная перестройка:**
   - Render Dashboard → Settings → Delete
   - Создать новый service
   - Заново связать репозиторий
   - Deploy

3. **На Docker - с нулей:**
   ```bash
   docker stop armedmusic
   docker rm armedmusic
   docker rmi armedmusic
   docker build -t armedmusic .
   docker run --env-file .env armedmusic
   ```

---

**Помните:** Большинство ошибок - это транзиентные проблемы, которые решаются автоматически! 🤖
