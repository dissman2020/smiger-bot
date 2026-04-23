#!/bin/bash

# Smiger Bot Test Runner

set -e

echo "======================================"
echo "Smiger Bot Test Suite"
echo "======================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: Please run from backend directory${NC}"
    exit 1
fi

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q -r requirements-test.txt

echo ""
echo "======================================"
echo "Running Tests"
echo "======================================"

# Parse arguments
TEST_TYPE=${1:-all}

if [ "$TEST_TYPE" = "unit" ] || [ "$TEST_TYPE" = "all" ]; then
    echo ""
    echo -e "${YELLOW}Running Unit Tests...${NC}"
    pytest tests/unit -v --tb=short -m "not integration" || true
fi

if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    echo ""
    echo -e "${YELLOW}Running Integration Tests...${NC}"
    pytest tests/integration -v --tb=short || true
fi

if [ "$TEST_TYPE" = "auth" ]; then
    echo ""
    echo -e "${YELLOW}Running Auth Tests...${NC}"
    pytest tests/unit/test_auth.py -v --tb=short
fi

if [ "$TEST_TYPE" = "chat" ]; then
    echo ""
    echo -e "${YELLOW}Running Chat Tests...${NC}"
    pytest tests/unit/test_chat.py -v --tb=short
fi

if [ "$TEST_TYPE" = "knowledge" ]; then
    echo ""
    echo -e "${YELLOW}Running Knowledge Tests...${NC}"
    pytest tests/unit/test_knowledge.py -v --tb=short
fi

if [ "$TEST_TYPE" = "faq" ]; then
    echo ""
    echo -e "${YELLOW}Running FAQ Tests...${NC}"
    pytest tests/unit/test_faq.py -v --tb=short
fi

if [ "$TEST_TYPE" = "lead" ]; then
    echo ""
    echo -e "${YELLOW}Running Lead Tests...${NC}"
    pytest tests/unit/test_leads.py -v --tb=short
fi

if [ "$TEST_TYPE" = "handoff" ]; then
    echo ""
    echo -e "${YELLOW}Running Handoff Tests...${NC}"
    pytest tests/unit/test_handoff.py -v --tb=short
fi

if [ "$TEST_TYPE" = "rag" ]; then
    echo ""
    echo -e "${YELLOW}Running RAG Tests...${NC}"
    pytest tests/unit/test_rag.py -v --tb=short
fi

if [ "$TEST_TYPE" = "security" ]; then
    echo ""
    echo -e "${YELLOW}Running Security Tests...${NC}"
    pytest tests/unit/test_security.py -v --tb=short
fi

if [ "$TEST_TYPE" = "coverage" ]; then
    echo ""
    echo -e "${YELLOW}Running Tests with Coverage...${NC}"
    pytest tests/unit -v --cov=app --cov-report=html --cov-report=term
fi

echo ""
echo "======================================"
echo -e "${GREEN}Test Run Complete${NC}"
echo "======================================"

# Usage info
echo ""
echo "Usage:"
echo "  ./run_tests.sh           # Run all tests"
echo "  ./run_tests.sh unit      # Run unit tests only"
echo "  ./run_tests.sh integration # Run integration tests"
echo "  ./run_tests.sh auth      # Run auth tests only"
echo "  ./run_tests.sh chat      # Run chat tests only"
echo "  ./run_tests.sh coverage  # Run with coverage report"
