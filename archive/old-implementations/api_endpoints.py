"""
Enhanced API endpoints for account management
To be integrated into simple_app.py
"""

# Add these routes to simple_app.py after the existing routes

@app.route('/api/accounts/<account_id>/health')
@login_required
def api_account_health(account_id):
    """Get real-time health status for an account"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("""
        SELECT smtp_health_status, imap_health_status, pop3_health_status,
               last_health_check, last_error, connection_status
        FROM email_accounts WHERE id = ?
    """, (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Determine overall status
    smtp_status = account['smtp_health_status'] or 'unknown'
    imap_status = account['imap_health_status'] or 'unknown'
    pop3_status = account['pop3_health_status'] or 'unknown'
    
    if smtp_status == 'connected' and imap_status == 'connected':
        overall = 'connected'
    elif smtp_status == 'error' or imap_status == 'error':
        overall = 'error'
    elif smtp_status == 'unknown' and imap_status == 'unknown':
        overall = 'unknown'
    else:
        overall = 'warning'
    
    conn.close()
    
    return jsonify({
        'overall': overall,
        'smtp': smtp_status,
        'imap': imap_status,
        'pop3': pop3_status,
        'last_check': account['last_health_check'],
        'last_error': account['last_error']
    })@app.route('/api/accounts/<account_id>/test', methods=['POST'])
@login_required
def api_test_account(account_id):
    """Test account connections and update health status"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Decrypt passwords
    imap_password = decrypt_credential(account['imap_password'])
    smtp_password = decrypt_credential(account['smtp_password'])
    
    # Test connections
    imap_success, imap_msg = test_email_connection('imap', account['imap_host'], 
                                                   account['imap_port'], account['imap_username'], 
                                                   imap_password, account['imap_use_ssl'])
    
    smtp_success, smtp_msg = test_email_connection('smtp', account['smtp_host'], 
                                                   account['smtp_port'], account['smtp_username'], 
                                                   smtp_password, account['smtp_use_ssl'])
    
    # Update health status
    cursor.execute("""
        UPDATE email_accounts 
        SET smtp_health_status = ?, imap_health_status = ?, 
            last_health_check = CURRENT_TIMESTAMP,
            connection_status = ?
        WHERE id = ?
    """, (
        'connected' if smtp_success else 'error',
        'connected' if imap_success else 'error',
        'connected' if (smtp_success and imap_success) else 'error',
        account_id
    ))
    
    if smtp_success and imap_success:
        cursor.execute("""
            UPDATE email_accounts 
            SET last_successful_connection = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (account_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': smtp_success and imap_success,
        'imap': {'success': imap_success, 'message': imap_msg},
        'smtp': {'success': smtp_success, 'message': smtp_msg}
    })@app.route('/api/accounts/<account_id>', methods=['GET'])
@login_required
def api_get_account(account_id):
    """Get account details for editing"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Don't send encrypted passwords
    account_data = dict(account)
    account_data.pop('imap_password', None)
    account_data.pop('smtp_password', None)
    account_data.pop('pop3_password', None)
    
    conn.close()
    return jsonify(account_data)

@app.route('/api/accounts/<account_id>', methods=['PUT'])
@login_required
def api_update_account(account_id):
    """Update account settings"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if account exists
    account = cursor.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Build update query dynamically
    update_fields = []
    update_values = []
    
    # Update basic fields
    if 'account_name' in data:
        update_fields.append("account_name = ?")
        update_values.append(data['account_name'])
    
    if 'email_address' in data:
        update_fields.append("email_address = ?")
        update_values.append(data['email_address'])
    
    if 'provider_type' in data:
        update_fields.append("provider_type = ?")
        update_values.append(data['provider_type'])
    
    # SMTP fields
    if 'smtp_host' in data:
        update_fields.append("smtp_host = ?")
        update_values.append(data['smtp_host'])
    
    if 'smtp_port' in data:
        update_fields.append("smtp_port = ?")
        update_values.append(data['smtp_port'])
    
    if 'smtp_username' in data:
        update_fields.append("smtp_username = ?")
        update_values.append(data['smtp_username'])
    
    if 'smtp_password' in data and data['smtp_password']:
        update_fields.append("smtp_password = ?")
        update_values.append(encrypt_credential(data['smtp_password']))
    
    if 'smtp_use_ssl' in data:
        update_fields.append("smtp_use_ssl = ?")
        update_values.append(1 if data['smtp_use_ssl'] else 0)
    
    # IMAP fields
    if 'imap_host' in data:
        update_fields.append("imap_host = ?")
        update_values.append(data['imap_host'])
    
    if 'imap_port' in data:
        update_fields.append("imap_port = ?")
        update_values.append(data['imap_port'])
    
    if 'imap_username' in data:
        update_fields.append("imap_username = ?")
        update_values.append(data['imap_username'])
    
    if 'imap_password' in data and data['imap_password']:
        update_fields.append("imap_password = ?")
        update_values.append(encrypt_credential(data['imap_password']))
    
    if 'imap_use_ssl' in data:
        update_fields.append("imap_use_ssl = ?")
        update_values.append(1 if data['imap_use_ssl'] else 0)
    
    # Update timestamp
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    # Execute update
    if update_fields:
        update_values.append(account_id)
        query = f"UPDATE email_accounts SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})@app.route('/api/accounts/<account_id>', methods=['DELETE'])
@login_required
def api_delete_account(account_id):
    """Delete an account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Stop monitoring thread if running
    if int(account_id) in imap_threads:
        del imap_threads[int(account_id)]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Account not found'}), 404

@app.route('/api/accounts/export')
@login_required
def api_export_accounts():
    """Export accounts to JSON (without passwords)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    accounts = cursor.execute("""
        SELECT account_name, email_address, provider_type,
               imap_host, imap_port, imap_username, imap_use_ssl,
               smtp_host, smtp_port, smtp_username, smtp_use_ssl,
               pop3_host, pop3_port, pop3_username, pop3_use_ssl
        FROM email_accounts
        ORDER BY account_name
    """).fetchall()
    
    conn.close()
    
    export_data = {
        'version': '1.0',
        'exported_at': datetime.now().isoformat(),
        'accounts': [dict(account) for account in accounts]
    }
    
    response = jsonify(export_data)
    response.headers['Content-Disposition'] = 'attachment; filename=email_accounts_export.json'
    return response