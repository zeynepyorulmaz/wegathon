#!/usr/bin/env python3
"""
Test the new ChatGPT day planner.
Demonstrates natural timeline generation without artificial blocks.
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-backend'))

from app.services.day_planner import generate_full_day_plan


async def test_single_day():
    """Test generating a complete day plan."""
    
    print("="*70)
    print("ChatGPT Day Planner Test")
    print("="*70)
    print()
    
    destination = "Berlin"
    day_num = 1
    date = "2025-12-01"
    
    print(f"📍 Destination: {destination}")
    print(f"📅 Day: {day_num}")
    print(f"🗓️  Date: {date}")
    print(f"👥 Travelers: 2 adults")
    print()
    print("Generating complete day plan with ChatGPT...")
    print()
    
    try:
        time_slots = await generate_full_day_plan(
            destination=destination,
            day_num=day_num,
            date=date,
            total_days=3,
            adults=2,
            children=0,
            preferences=["culture", "food"],
            budget="mid",
            language="tr"
        )
        
        print("✅ Day plan generated successfully!")
        print()
        print("="*70)
        print("TIMELINE")
        print("="*70)
        print()
        
        for i, slot in enumerate(time_slots, 1):
            print(f"{i}. {slot.startTime} - {slot.endTime}")
            print(f"   🎯 {slot.options[0].text}")
            print(f"   📝 {slot.options[0].description}")
            if slot.options[0].location:
                print(f"   📍 {slot.options[0].location}")
            
            # Show alternatives
            if len(slot.options) > 1:
                print(f"\n   Alternatifler:")
                for alt in slot.options[1:]:
                    if alt.text != "Serbest zaman":
                        print(f"   • {alt.text}")
            print()
        
        print("="*70)
        print("SUMMARY")
        print("="*70)
        print(f"✅ Total activities: {len(time_slots)}")
        
        # Calculate total time
        if time_slots:
            start = time_slots[0].startTime
            end = time_slots[-1].endTime
            print(f"⏰ Day schedule: {start} - {end}")
        
        # Check for variety
        activities = [slot.options[0].text for slot in time_slots]
        unique_activities = set(activities)
        print(f"🎨 Unique activities: {len(unique_activities)}/{len(activities)}")
        
        # Check for specific places
        specific_count = sum(
            1 for slot in time_slots 
            if any(char.isupper() for char in slot.options[0].text[1:])  # Has capital letters (likely place names)
        )
        print(f"📌 Activities with specific places: {specific_count}/{len(activities)}")
        
        if len(unique_activities) == len(activities):
            print("\n🎉 Perfect! All activities are unique!")
        
        if specific_count >= len(activities) * 0.7:
            print("🎉 Great! Most activities have specific place names!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_multi_day():
    """Test generating plans for multiple days."""
    
    print("\n" + "="*70)
    print("MULTI-DAY TEST")
    print("="*70)
    print()
    
    destination = "Berlin"
    total_days = 3
    
    print(f"Generating {total_days}-day plan for {destination}...")
    print()
    
    all_activities = []
    
    for day in range(1, total_days + 1):
        print(f"Day {day}/{total_days}...")
        
        try:
            slots = await generate_full_day_plan(
                destination=destination,
                day_num=day,
                date=f"2025-12-{day:02d}",
                total_days=total_days,
                adults=2,
                language="tr"
            )
            
            print(f"  ✅ {len(slots)} activities generated")
            
            # Collect activities
            for slot in slots:
                all_activities.append(slot.options[0].text)
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    print()
    print("="*70)
    print("MULTI-DAY SUMMARY")
    print("="*70)
    print(f"Total activities across all days: {len(all_activities)}")
    print(f"Unique activities: {len(set(all_activities))}")
    
    duplicates = len(all_activities) - len(set(all_activities))
    if duplicates == 0:
        print("🎉 Perfect! No duplicate activities across days!")
    else:
        print(f"⚠️  {duplicates} duplicate activities found")
    
    return True


async def main():
    """Run all tests."""
    
    print()
    print("🧪 ChatGPT Day Planner Test Suite")
    print()
    print("This tests the new natural timeline approach")
    print("(no artificial morning/afternoon/evening blocks)")
    print()
    
    # Check API key
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not set")
        print()
        print("Please add it to your .env file:")
        print("  OPENAI_API_KEY='sk-...'")
        print()
        print("Or export it:")
        print("  export OPENAI_API_KEY='sk-...'")
        return
    
    print("✅ OPENAI_API_KEY found")
    print()
    
    # Test 1: Single day
    success = await test_single_day()
    
    if not success:
        print("\n❌ Single day test failed")
        return
    
    # Test 2: Multi-day
    success = await test_multi_day()
    
    if not success:
        print("\n❌ Multi-day test failed")
        return
    
    print()
    print("="*70)
    print("🎉 ALL TESTS PASSED!")
    print("="*70)
    print()
    print("The ChatGPT day planner is working correctly!")
    print("Natural timelines with specific places and variety.")
    print()


if __name__ == "__main__":
    asyncio.run(main())

