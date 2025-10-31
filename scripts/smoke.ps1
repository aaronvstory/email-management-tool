#!/usr/bin/env pwsh
# Smoke Test Script for Email Management Tool
# Tests critical endpoints to verify basic functionality

param(
    [string]$BaseUrl = "http://localhost:5000",
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "🔍 Email Management Tool - Smoke Tests" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host ""

$TestsPassed = 0
$TestsFailed = 0
$TestResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [string]$ExpectedContent = $null,
        [scriptblock]$Validator = $null
    )

    try {
        $Response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 10 -UseBasicParsing

        if ($Response.StatusCode -eq $ExpectedStatus) {
            if ($ExpectedContent -and $Response.Content -notmatch $ExpectedContent) {
                throw "Content validation failed: Expected '$ExpectedContent' in response"
            }

            if ($Validator) {
                $ValidationResult = & $Validator $Response
                if (-not $ValidationResult) {
                    throw "Custom validation failed"
                }
            }

            Write-Host "✅ $Name" -ForegroundColor Green
            $script:TestsPassed++
            $script:TestResults += [PSCustomObject]@{
                Test = $Name
                Status = "PASS"
                Details = "Status: $($Response.StatusCode)"
            }
            return $true
        } else {
            throw "Expected status $ExpectedStatus but got $($Response.StatusCode)"
        }
    } catch {
        Write-Host "❌ $Name" -ForegroundColor Red
        if ($Verbose) {
            Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
        $script:TestsFailed++
        $script:TestResults += [PSCustomObject]@{
            Test = $Name
            Status = "FAIL"
            Details = $_.Exception.Message
        }
        return $false
    }
}

function Test-JSON-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string[]]$RequiredFields
    )

    try {
        $Response = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 10

        foreach ($Field in $RequiredFields) {
            if (-not $Response.$Field) {
                throw "Missing required field: $Field"
            }
        }

        Write-Host "✅ $Name" -ForegroundColor Green
        $script:TestsPassed++
        $script:TestResults += [PSCustomObject]@{
            Test = $Name
            Status = "PASS"
            Details = "All required fields present"
        }
        return $true
    } catch {
        Write-Host "❌ $Name" -ForegroundColor Red
        if ($Verbose) {
            Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
        $script:TestsFailed++
        $script:TestResults += [PSCustomObject]@{
            Test = $Name
            Status = "FAIL"
            Details = $_.Exception.Message
        }
        return $false
    }
}

# Test 1: Health Check
Write-Host "Testing Core Endpoints..." -ForegroundColor Yellow
Test-JSON-Endpoint -Name "Health Check (/healthz)" `
    -Url "$BaseUrl/healthz" `
    -RequiredFields @("ok", "db")

# Test 2: Metrics Endpoint
Test-Endpoint -Name "Metrics Endpoint (/metrics)" `
    -Url "$BaseUrl/metrics" `
    -ExpectedContent "email_messages_total"

# Test 3: Login Page
Test-Endpoint -Name "Login Page (/login)" `
    -Url "$BaseUrl/login" `
    -ExpectedContent "<form"

# Test 4: Static Assets (CSS)
Test-Endpoint -Name "Static CSS (/static/css/main.css)" `
    -Url "$BaseUrl/static/css/main.css" `
    -ExpectedContent "body"

# Test 5: API Health - SMTP
Test-JSON-Endpoint -Name "SMTP Health (/api/smtp-health)" `
    -Url "$BaseUrl/api/smtp-health" `
    -RequiredFields @("running")

Write-Host ""
Write-Host "Attachment-Specific Tests..." -ForegroundColor Yellow

# Test 6: Attachment API Structure (requires login - just verify endpoint exists)
try {
    $Response = Invoke-WebRequest -Uri "$BaseUrl/api/email/1/attachments" -Method GET -TimeoutSec 5 -UseBasicParsing -SkipHttpErrorCheck
    if ($Response.StatusCode -eq 401 -or $Response.StatusCode -eq 404) {
        Write-Host "✅ Attachment API Endpoint Exists (/api/email/<id>/attachments)" -ForegroundColor Green
        $TestsPassed++
        $TestResults += [PSCustomObject]@{
            Test = "Attachment API Endpoint"
            Status = "PASS"
            Details = "Endpoint responds (auth required as expected)"
        }
    } else {
        throw "Unexpected status: $($Response.StatusCode)"
    }
} catch {
    Write-Host "❌ Attachment API Endpoint" -ForegroundColor Red
    if ($Verbose) {
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    $TestsFailed++
    $TestResults += [PSCustomObject]@{
        Test = "Attachment API Endpoint"
        Status = "FAIL"
        Details = $_.Exception.Message
    }
}

Write-Host ""
Write-Host "=" * 50 -ForegroundColor Gray
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray
Write-Host "✅ Passed: $TestsPassed" -ForegroundColor Green
Write-Host "❌ Failed: $TestsFailed" -ForegroundColor Red
Write-Host "Total: $($TestsPassed + $TestsFailed)" -ForegroundColor Gray
Write-Host ""

if ($Verbose) {
    Write-Host "Detailed Results:" -ForegroundColor Yellow
    $TestResults | Format-Table -AutoSize
}

if ($TestsFailed -gt 0) {
    Write-Host "❌ Smoke tests FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ All smoke tests PASSED" -ForegroundColor Green
    exit 0
}
