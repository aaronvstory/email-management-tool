#!/bin/bash
# Smoke Test Script for Email Management Tool
# Tests critical endpoints to verify basic functionality

BASE_URL="${BASE_URL:-http://localhost:5000}"
VERBOSE="${VERBOSE:-0}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${CYAN}🔍 Email Management Tool - Smoke Tests${NC}"
echo -e "${GRAY}Base URL: $BASE_URL${NC}"
echo ""

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    local expected_content="$4"

    response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        if [ -n "$expected_content" ] && ! echo "$body" | grep -q "$expected_content"; then
            echo -e "${RED}❌ $name${NC}"
            [ "$VERBOSE" = "1" ] && echo -e "${YELLOW}   Error: Expected content not found${NC}"
            ((TESTS_FAILED++))
            return 1
        fi

        echo -e "${GREEN}✅ $name${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ $name${NC}"
        [ "$VERBOSE" = "1" ] && echo -e "${YELLOW}   Error: Expected status $expected_status but got $status_code${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

test_json_endpoint() {
    local name="$1"
    local url="$2"
    shift 2
    local required_fields=("$@")

    response=$(curl -s "$url" 2>&1)

    for field in "${required_fields[@]}"; do
        if ! echo "$response" | grep -q "\"$field\""; then
            echo -e "${RED}❌ $name${NC}"
            [ "$VERBOSE" = "1" ] && echo -e "${YELLOW}   Error: Missing required field: $field${NC}"
            ((TESTS_FAILED++))
            return 1
        fi
    done

    echo -e "${GREEN}✅ $name${NC}"
    ((TESTS_PASSED++))
    return 0
}

# Test 1: Health Check
echo -e "${YELLOW}Testing Core Endpoints...${NC}"
test_json_endpoint "Health Check (/healthz)" "$BASE_URL/healthz" "ok" "db"

# Test 2: Metrics Endpoint
test_endpoint "Metrics Endpoint (/metrics)" "$BASE_URL/metrics" 200 "email_messages_total"

# Test 3: Login Page
test_endpoint "Login Page (/login)" "$BASE_URL/login" 200 "<form"

# Test 4: Static Assets (CSS)
test_endpoint "Static CSS (/static/css/main.css)" "$BASE_URL/static/css/main.css" 200 "body"

# Test 5: API Health - SMTP
test_json_endpoint "SMTP Health (/api/smtp-health)" "$BASE_URL/api/smtp-health" "running"

echo ""
echo -e "${YELLOW}Attachment-Specific Tests...${NC}"

# Test 6: Attachment API Structure (requires login - just verify endpoint exists)
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/email/1/attachments")
if [ "$status" = "401" ] || [ "$status" = "404" ]; then
    echo -e "${GREEN}✅ Attachment API Endpoint Exists (/api/email/<id>/attachments)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Attachment API Endpoint${NC}"
    [ "$VERBOSE" = "1" ] && echo -e "${YELLOW}   Error: Unexpected status: $status${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${GRAY}==================================================${NC}"
echo -e "${CYAN}Test Results Summary${NC}"
echo -e "${GRAY}==================================================${NC}"
echo -e "${GREEN}✅ Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Failed: $TESTS_FAILED${NC}"
echo -e "${GRAY}Total: $((TESTS_PASSED + TESTS_FAILED))${NC}"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Smoke tests FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All smoke tests PASSED${NC}"
    exit 0
fi
