# Create the main application structure for the email moderation system
import os
import json

# Create directory structure
directories = [
    "email_moderation_system",
    "email_moderation_system/app",
    "email_moderation_system/config",
    "email_moderation_system/static",
    "email_moderation_system/static/css",
    "email_moderation_system/static/js",
    "email_moderation_system/templates",
    "email_moderation_system/data",
    "email_moderation_system/logs"
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

print("\nDirectory structure created successfully!")