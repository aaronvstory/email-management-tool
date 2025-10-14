# Create message detail view template
message_detail_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Message Details - Email Moderation System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="fas fa-envelope-open-text"></i> Email Moderation System
            </a>
            <div class="navbar-nav">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('queue') }}">Queue</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Message Details</h1>
            <div>
                <a href="{{ url_for('queue') }}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Queue
                </a>
                {% if email.status == 'PENDING' %}
                <a href="{{ url_for('edit_message', message_id=email.message_id) }}" class="btn btn-warning">
                    <i class="fas fa-edit"></i> Edit Message
                </a>
                {% endif %}
            </div>
        </div>

        {% if email.error %}
            <div class="alert alert-danger">
                <h5>Error</h5>
                <p>{{ email.error }}</p>
            </div>
        {% else %}
        
        <!-- Message Headers -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Message Information</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <table class="table table-sm">
                            <tr>
                                <th>Message ID:</th>
                                <td><code>{{ email.message_id }}</code></td>
                            </tr>
                            <tr>
                                <th>From:</th>
                                <td>{{ email.sender }}</td>
                            </tr>
                            <tr>
                                <th>To:</th>
                                <td>
                                    {% for recipient in email.recipients %}
                                        <span class="badge bg-light text-dark me-1">{{ recipient }}</span>
                                    {% endfor %}
                                </td>
                            </tr>
                            <tr>
                                <th>Subject:</th>
                                <td>{{ email.subject }}</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <table class="table table-sm">
                            <tr>
                                <th>Date:</th>
                                <td>{{ email.date }}</td>
                            </tr>
                            <tr>
                                <th>Status:</th>
                                <td>
                                    <span class="badge bg-{{ 'warning' if email.status == 'PENDING' else 'success' if email.status == 'APPROVED' else 'danger' if email.status == 'REJECTED' else 'info' }}">
                                        {{ email.status }}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <th>Keywords Matched:</th>
                                <td>
                                    {% if email.keywords_matched %}
                                        {% for keyword in email.keywords_matched %}
                                            <span class="badge bg-warning text-dark me-1">{{ keyword }}</span>
                                        {% endfor %}
                                    {% else %}
                                        <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                            </tr>
                            <tr>
                                <th>Attachments:</th>
                                <td>
                                    {% if email.attachments %}
                                        <span class="badge bg-info">{{ email.attachments|length }} files</span>
                                    {% else %}
                                        <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Attachments -->
        {% if email.attachments %}
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Attachments</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    {% for attachment in email.attachments %}
                    <div class="col-md-6 mb-2">
                        <div class="card">
                            <div class="card-body py-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>{{ attachment.filename }}</strong><br>
                                        <small class="text-muted">{{ attachment.content_type }} • {{ (attachment.size / 1024) | round(1) }} KB</small>
                                    </div>
                                    <div>
                                        <i class="fas fa-paperclip text-muted"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Message Content -->
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Message Content</h5>
                <div class="btn-group btn-group-sm" role="group">
                    <input type="radio" class="btn-check" name="content-view" id="text-view" autocomplete="off" checked>
                    <label class="btn btn-outline-secondary" for="text-view">Text</label>
                    
                    {% if email.body_html %}
                    <input type="radio" class="btn-check" name="content-view" id="html-view" autocomplete="off">
                    <label class="btn btn-outline-secondary" for="html-view">HTML</label>
                    {% endif %}
                </div>
            </div>
            <div class="card-body">
                <div id="text-content">
                    <pre class="bg-light p-3" style="white-space: pre-wrap;">{{ email.body_text or 'No text content' }}</pre>
                </div>
                {% if email.body_html %}
                <div id="html-content" style="display: none;">
                    <div class="bg-light p-3">
                        <iframe srcdoc="{{ email.body_html }}" style="width: 100%; height: 400px; border: none;"></iframe>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Action Buttons -->
        {% if email.status == 'PENDING' %}
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Moderation Actions</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <button class="btn btn-success btn-lg w-100" onclick="approve_message()">
                            <i class="fas fa-check"></i> Approve & Send
                        </button>
                        <small class="text-muted">Send email as-is to recipients</small>
                    </div>
                    <div class="col-md-4">
                        <a href="{{ url_for('edit_message', message_id=email.message_id) }}" class="btn btn-warning btn-lg w-100">
                            <i class="fas fa-edit"></i> Edit & Approve
                        </a>
                        <small class="text-muted">Modify content before sending</small>
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-danger btn-lg w-100" onclick="reject_message()">
                            <i class="fas fa-times"></i> Reject
                        </button>
                        <small class="text-muted">Block email from being sent</small>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}

        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Toggle between text and HTML view
        document.querySelectorAll('input[name="content-view"]').forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.id === 'text-view') {
                    document.getElementById('text-content').style.display = 'block';
                    document.getElementById('html-content').style.display = 'none';
                } else if (this.id === 'html-view') {
                    document.getElementById('text-content').style.display = 'none';
                    document.getElementById('html-content').style.display = 'block';
                }
            });
        });

        function approve_message() {
            if (confirm('Approve and send this message?')) {
                // TODO: Implement approve action
                alert('Approve functionality coming soon!');
            }
        }

        function reject_message() {
            if (confirm('Reject this message? It will not be sent.')) {
                // TODO: Implement reject action
                alert('Reject functionality coming soon!');
            }
        }
    </script>
</body>
</html>'''

with open("email_moderation_system/templates/message_detail.html", "w") as f:
    f.write(message_detail_template)

print("Created message_detail.html template")
print("✓ Detailed message view with headers")
print("✓ Text/HTML content toggle")
print("✓ Attachment information")
print("✓ Moderation action buttons")