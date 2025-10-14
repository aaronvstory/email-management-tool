# Create requirements.txt
requirements_content = """aiosmtpd==1.4.6
flask==3.0.3
flask-sqlalchemy==3.1.1
email-validator==2.1.1
dkimpy==1.0.5
cryptography==42.0.8
dnspython==2.6.1
python-dateutil==2.9.0.post0
werkzeug==3.0.3
jinja2==3.1.4
requests==2.32.3
sqlite3
imaplib
smtplib
asyncio
threading
logging
configparser
"""

with open("email_moderation_system/requirements.txt", "w") as f:
    f.write(requirements_content)

print("Created requirements.txt")
print(requirements_content)