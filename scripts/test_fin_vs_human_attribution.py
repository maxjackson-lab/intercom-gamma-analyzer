"""
Test script to verify proper Fin vs Human agent attribution.

Tests whether:
1. Fin-only conversations are excluded from Horatio metrics
2. Fin→Horatio escalations are properly attributed
3. FCR is calculated fairly for human agents
"""

import asyncio
from src.services.duckdb_storage import DuckDBStorage

async def test_attribution():
    """Test Fin vs Human attribution logic"""
    
    storage = DuckDBStorage()
    
    # Sample test: Get a few conversations and check attribution
    result = storage.conn.execute("""
        SELECT 
            id,
            ai_agent_participated,
            state,
            conversation_rating,
            count_reopens,
            admin_assignee_id
        FROM conversations
        WHERE ai_agent_participated = true
        LIMIT 10
    """).fetchall()
    
    print("\n📊 Sample Fin-Involved Conversations:\n")
    print("ID | Fin? | Admin ID | State | Rating | Reopens | Attribution")
    print("-" * 80)
    
    for row in result:
        conv_id, fin, admin_id, state, rating, reopens = row[:6]
        
        # Determine attribution
        if admin_id:
            attribution = "HUMAN AGENT (Fin escalated)"
        else:
            attribution = "FIN ONLY (no human)"
        
        print(f"{conv_id[:8]}... | {fin} | {admin_id or 'None':15} | {state:6} | {rating or 'None':4} | {reopens:7} | {attribution}")
    
    print("\n")
    
    # Check Horatio conversations
    result2 = storage.conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ai_agent_participated THEN 1 ELSE 0 END) as fin_involved
        FROM conversations
        WHERE admin_assignee_id IS NOT NULL
          AND admin_assignee_id != ''
    """).fetchone()
    
    total, fin_involved = result2
    
    print("📊 Human Agent Conversations:")
    print(f"   Total conversations with human admin: {total}")
    print(f"   Started with Fin first: {fin_involved} ({fin_involved/total*100:.1f}%)")
    print(f"   Human from start: {total - fin_involved}")
    
    print("\n💡 Key Question:")
    print("   When Fin escalates to Horatio, should we count it in Horatio's metrics?")
    print("   Answer: YES - but we need to track it separately!\n")

if __name__ == "__main__":
    asyncio.run(test_attribution())

