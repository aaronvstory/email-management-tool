# 🚀 How to Launch the Email Management Tool

## ✅ Your Application is Already Running!

The application is currently running and accessible at:
- **Web Dashboard**: http://localhost:5000
- **SMTP Proxy**: localhost:8587
- **Default Login**: `admin` / `admin123`

## 📧 Access the New Unified Email Management

Open your browser and go to:
```
http://localhost:5000/emails-unified
```

Or simply click on **"Emails"** in the navigation menu.

## 🔄 Starting/Stopping the Application

### To Start (if not running):
```batch
launch.bat
```
This will:
- Check for port conflicts
- Start the Flask application
- Open the dashboard in your browser

### Alternative Start Methods:
```batch
# Method 1: Using Python directly
python simple_app.py

# Method 2: Using the start script
python start.py

# Method 3: Using PowerShell management
powershell .\manage.ps1 start
```

### To Stop:
- Press `Ctrl+C` in the console window where the app is running
- Or use PowerShell: `powershell .\manage.ps1 stop`

## 🎯 Quick Access URLs

| Feature | URL |
|---------|-----|
| **Unified Email Management** | http://localhost:5000/emails-unified |
| Dashboard | http://localhost:5000/dashboard |
| Compose Email | http://localhost:5000/compose |
| Accounts | http://localhost:5000/accounts |
| Rules | http://localhost:5000/rules |
| Diagnostics | http://localhost:5000/diagnostics |

## 🔍 Check if Application is Running

### Method 1: Browser
Open: http://localhost:5000/healthz

You should see JSON response like:
```json
{
  "ok": true,
  "held_count": 0,
  "released_24h": 0,
  "db": "ok"
}
```

### Method 2: Command Line
```powershell
# Check if port 5000 is listening
netstat -an | findstr :5000

# Check application status
powershell .\manage.ps1 status
```

## 📱 Using the Unified Email Interface

1. **Navigate to**: http://localhost:5000/emails-unified
2. **Select an account** from the dropdown (if you have multiple)
3. **Use tabs** to filter emails:
   - All - View all emails
   - Held - Emails intercepted and held
   - Pending - Emails awaiting approval
   - Approved - Approved emails
   - Rejected - Rejected emails
4. **Search** using the search box
5. **Click actions** on each email:
   - Edit - Modify email content
   - Release - Send to inbox
   - Approve - Approve for sending
   - Reject - Reject email
   - Discard - Permanently remove

## 🛠️ Troubleshooting

### Port Already in Use
If you see "Port 5000 is in use":
```batch
# The launch.bat script will detect and handle this automatically
# Or manually kill the process:
netstat -ano | findstr :5000
taskkill /F /PID <process_id>
```

### Application Won't Start
1. Check Python is installed: `python --version`
2. Install dependencies: `pip install -r requirements.txt`
3. Check logs: `type logs\email_moderation.log`

### Can't Access Dashboard
1. Make sure application is running
2. Try http://127.0.0.1:5000 instead of localhost
3. Check firewall settings for port 5000

## 📊 Application Status

Your application is currently:
- ✅ Running on port 5000
- ✅ Healthy and responding
- ✅ Ready to use the new unified interface

## 🎉 Next Steps

1. Open http://localhost:5000/emails-unified
2. Log in with: `admin` / `admin123`
3. Start managing your emails in the new unified interface!

---

**Need Help?** Check the main README.md or the IMPLEMENTATION_SUMMARY.md for more details.