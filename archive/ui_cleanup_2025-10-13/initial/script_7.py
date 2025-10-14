# Create HTML templates for the web interface

# Dashboard template
dashboard_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Moderation Dashboard</title>
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
        <!-- Flash messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <h1 class="mb-4">Email Moderation Dashboard</h1>
        
        <!-- Statistics Cards -->
        <div class="row mb-4">
            <div class="col-md-2">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{{ stats.total }}</h4>
                                <p class="mb-0">Total Emails</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-envelope fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-warning text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{{ stats.pending }}</h4>
                                <p class="mb-0">Pending</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-clock fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{{ stats.approved }}</h4>
                                <p class="mb-0">Approved</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-check fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-danger text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{{ stats.rejected }}</h4>
                                <p class="mb-0">Rejected</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-times fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-info text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{{ stats.sent }}</h4>
                                <p class="mb-0">Sent</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-paper-plane fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Messages -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Recent Messages</h5>
                <a href="{{ url_for('queue') }}" class="btn btn-primary btn-sm">View All</a>
            </div>
            <div class="card-body">
                {% if recent_messages %}
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Sender</th>
                                    <th>Subject</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for message in recent_messages %}
                                <tr>
                                    <td>{{ message.sender }}</td>
                                    <td>{{ message.subject or 'No Subject' }}</td>
                                    <td>
                                        <span class="badge bg-{{ 'warning' if message.status == 'PENDING' else 'success' if message.status == 'APPROVED' else 'danger' if message.status == 'REJECTED' else 'info' }}">
                                            {{ message.status }}
                                        </span>
                                    </td>
                                    <td>{{ message.created_at }}</td>
                                    <td>
                                        <a href="{{ url_for('view_message', message_id=message.message_id) }}" class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-eye"></i> View
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <p class="text-muted">No messages found.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''

with open("email_moderation_system/templates/dashboard.html", "w") as f:
    f.write(dashboard_template)

print("Created dashboard.html template")
print("✓ Bootstrap-styled dashboard")
print("✓ Statistics cards for queue metrics") 
print("✓ Recent messages table")
print("✓ Responsive design")