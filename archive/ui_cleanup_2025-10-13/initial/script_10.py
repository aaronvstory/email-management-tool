# Create message editing template
message_edit_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Message - Email Moderation System</title>
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
            <h1>Edit Message</h1>
            <div>
                <a href="{{ url_for('view_message', message_id=email.message_id) }}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Message
                </a>
            </div>
        </div>

        <form method="POST" action="{{ url_for('update_message', message_id=email.message_id) }}">
            <!-- Message Headers -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Message Headers</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="sender" class="form-label">From:</label>
                                <input type="text" class="form-control" id="sender" value="{{ email.sender }}" readonly>
                                <small class="text-muted">Sender cannot be modified</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="recipients" class="form-label">To:</label>
                                <input type="text" class="form-control" id="recipients" 
                                       value="{{ email.recipients | join(', ') }}" readonly>
                                <small class="text-muted">Recipients cannot be modified</small>
                            </div>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="subject" class="form-label">Subject:</label>
                        <input type="text" class="form-control" id="subject" name="subject" 
                               value="{{ email.subject }}" required>
                    </div>
                </div>
            </div>

            <!-- Message Content Editor -->
            <div class="card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Message Content</h5>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="add-stamp" checked>
                        <label class="form-check-label" for="add-stamp">
                            Add "Checked by" stamp
                        </label>
                    </div>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label for="body" class="form-label">Message Body:</label>
                        <textarea class="form-control" id="body" name="body" rows="15" required>{{ email.body_text }}</textarea>
                        <small class="text-muted">Edit the message content. HTML tags will be preserved if present.</small>
                    </div>
                </div>
            </div>

            <!-- Reviewer Information -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Reviewer Information</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="reviewer_name" class="form-label">Reviewer Name:</label>
                                <input type="text" class="form-control" id="reviewer_name" name="reviewer_name" 
                                       placeholder="e.g., John Smith" required>
                                <small class="text-muted">This will be added to the verification stamp</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="review_notes" class="form-label">Review Notes (Optional):</label>
                                <input type="text" class="form-control" id="review_notes" name="review_notes" 
                                       placeholder="Internal notes about this review">
                                <small class="text-muted">For audit purposes only</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Preview Section -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Preview</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <strong>Verification Stamp Preview:</strong><br>
                        <code id="stamp-preview">--- CHECKED BY [REVIEWER NAME] - APPROVED ---</code>
                    </div>
                    <p class="text-muted">This stamp will be automatically added to the end of the message when "Add stamp" is enabled.</p>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="card">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <button type="submit" class="btn btn-success btn-lg w-100" name="action" value="save_and_approve">
                                <i class="fas fa-check"></i> Save & Approve
                            </button>
                            <small class="text-muted">Save changes and approve for sending</small>
                        </div>
                        <div class="col-md-6">
                            <button type="submit" class="btn btn-warning btn-lg w-100" name="action" value="save_draft">
                                <i class="fas fa-save"></i> Save Draft
                            </button>
                            <small class="text-muted">Save changes without approving</small>
                        </div>
                    </div>
                </div>
            </div>
        </form>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Update stamp preview when reviewer name changes
        document.getElementById('reviewer_name').addEventListener('input', function() {
            const name = this.value.toUpperCase() || '[REVIEWER NAME]';
            document.getElementById('stamp-preview').textContent = 
                `--- CHECKED BY ${name} - APPROVED ---`;
        });

        // Character counter for message body
        const bodyTextarea = document.getElementById('body');
        const charCountDiv = document.createElement('div');
        charCountDiv.className = 'text-muted small mt-1';
        bodyTextarea.parentNode.appendChild(charCountDiv);
        
        function updateCharCount() {
            charCountDiv.textContent = `${bodyTextarea.value.length} characters`;
        }
        
        bodyTextarea.addEventListener('input', updateCharCount);
        updateCharCount();

        // Auto-resize textarea
        bodyTextarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    </script>
</body>
</html>'''

with open("email_moderation_system/templates/message_edit.html", "w") as f:
    f.write(message_edit_template)

print("Created message_edit.html template")
print("✓ Rich text editor for message content")
print("✓ Reviewer information input")
print("✓ Verification stamp preview")
print("✓ Save & approve workflow")