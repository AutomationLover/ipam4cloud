#!/bin/bash

# AWS Sync Monitoring Dashboard
# Real-time monitoring with multiple views

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear_screen() {
    clear
    echo -e "${CYAN}🔍 AWS VPC Sync Monitor Dashboard${NC}"
    echo -e "${CYAN}==================================${NC}"
    echo "$(date)"
    echo ""
}

show_service_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    if docker compose -f containers/docker-compose.yml ps aws-sync | grep -q "Up"; then
        echo -e "   Status: ${GREEN}Running ✅${NC}"
        
        # Get health status
        HEALTH=$(docker inspect prefix_aws_sync --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "   Health: ${GREEN}Healthy ✅${NC}"
        elif [ "$HEALTH" = "unhealthy" ]; then
            echo -e "   Health: ${RED}Unhealthy ❌${NC}"
        else
            echo -e "   Health: ${YELLOW}$HEALTH${NC}"
        fi
        
        # Get restart count
        RESTART_COUNT=$(docker inspect prefix_aws_sync --format='{{.RestartCount}}' 2>/dev/null || echo "unknown")
        echo -e "   Restart Count: $RESTART_COUNT"
        
    else
        echo -e "   Status: ${RED}Not Running ❌${NC}"
    fi
    echo ""
}

show_recent_logs() {
    echo -e "${BLUE}📋 Recent Activity (last 10 lines):${NC}"
    docker compose -f containers/docker-compose.yml logs --tail=10 --no-log-prefix aws-sync | while IFS= read -r line; do
        if [[ "$line" == *"ERROR"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ "$line" == *"SUCCESS"* ]] || [[ "$line" == *"✅"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ "$line" == *"WARNING"* ]] || [[ "$line" == *"⚠️"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        else
            echo "$line"
        fi
    done
    echo ""
}

show_sync_summary() {
    echo -e "${BLUE}📈 Sync Summary:${NC}"
    
    # Count log entries
    if docker compose -f containers/docker-compose.yml exec -T aws-sync test -f logs/aws_sync.log 2>/dev/null; then
        TOTAL_LINES=$(docker compose -f containers/docker-compose.yml exec -T aws-sync wc -l logs/aws_sync.log 2>/dev/null | awk '{print $1}' || echo "0")
        ERROR_COUNT=$(docker compose -f containers/docker-compose.yml exec -T aws-sync grep -c "ERROR" logs/aws_sync.log 2>/dev/null || echo "0")
        SUCCESS_COUNT=$(docker compose -f containers/docker-compose.yml exec -T aws-sync grep -c "SUCCESS\|✅" logs/aws_sync.log 2>/dev/null || echo "0")
        
        echo "   Total log entries: $TOTAL_LINES"
        echo -e "   Successful operations: ${GREEN}$SUCCESS_COUNT${NC}"
        echo -e "   Errors: ${RED}$ERROR_COUNT${NC}"
    else
        echo "   Log file not yet created"
    fi
    
    # Show last successful sync
    LAST_SYNC=$(docker compose -f containers/docker-compose.yml logs aws-sync 2>/dev/null | grep "Sync cycle completed" | tail -1 | cut -d'|' -f2- || echo "No successful syncs yet")
    echo "   Last successful sync: $LAST_SYNC"
    echo ""
}

show_database_status() {
    echo -e "${BLUE}🗄️  Database Connection:${NC}"
    
    if docker compose -f containers/docker-compose.yml ps postgres | grep -q "Up"; then
        echo -e "   Database: ${GREEN}Running ✅${NC}"
        
        # Test connection from sync service
        if docker compose -f containers/docker-compose.yml exec -T aws-sync python -c "
from models import DatabaseManager
import os
try:
    db = DatabaseManager(os.getenv('DATABASE_URL'))
    session = db.get_session()
    session.execute('SELECT 1')
    session.close()
    print('Connection: OK')
except Exception as e:
    print(f'Connection: ERROR - {str(e)[:50]}')
" 2>/dev/null; then
            echo -e "   Connectivity: ${GREEN}OK ✅${NC}"
        else
            echo -e "   Connectivity: ${RED}Failed ❌${NC}"
        fi
    else
        echo -e "   Database: ${RED}Not Running ❌${NC}"
    fi
    echo ""
}

show_aws_status() {
    echo -e "${BLUE}☁️  AWS Connection:${NC}"
    
    if docker compose -f containers/docker-compose.yml exec -T aws-sync aws sts get-caller-identity --output text --query 'Account' 2>/dev/null; then
        echo -e "   AWS Access: ${GREEN}OK ✅${NC}"
        ACCOUNT=$(docker compose -f containers/docker-compose.yml exec -T aws-sync aws sts get-caller-identity --output text --query 'Account' 2>/dev/null)
        echo "   Account: $ACCOUNT"
    else
        echo -e "   AWS Access: ${RED}Failed ❌${NC}"
    fi
    echo ""
}

# Main monitoring function
monitor_loop() {
    while true; do
        clear_screen
        show_service_status
        show_database_status
        show_aws_status
        show_sync_summary
        show_recent_logs
        
        echo -e "${CYAN}Press Ctrl+C to stop monitoring, or wait 10 seconds for refresh...${NC}"
        sleep 10
    done
}

# Handle different modes
case "${1:-monitor}" in
    "monitor"|"")
        echo "Starting real-time monitoring (Ctrl+C to stop)..."
        sleep 2
        monitor_loop
        ;;
    "once")
        clear_screen
        show_service_status
        show_database_status  
        show_aws_status
        show_sync_summary
        show_recent_logs
        ;;
    "logs")
        echo -e "${BLUE}📋 Following AWS Sync Logs (Ctrl+C to stop):${NC}"
        docker compose -f containers/docker-compose.yml logs -f aws-sync
        ;;
    "errors")
        echo -e "${RED}❌ Recent Errors:${NC}"
        docker compose -f containers/docker-compose.yml logs aws-sync | grep "ERROR\|CRITICAL\|Exception" | tail -20
        ;;
    *)
        echo "Usage: $0 [monitor|once|logs|errors]"
        echo ""
        echo "  monitor (default) - Real-time dashboard"
        echo "  once              - Single status check"  
        echo "  logs              - Follow logs"
        echo "  errors            - Show recent errors"
        ;;
esac
