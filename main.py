from telethon import TelegramClient
from telethon.errors import UserPrivacyRestrictedError, ChannelPrivateError
import asyncio
import time
from config import API_ID, API_HASH, PHONE_NUMBER, SOURCE_GROUP, DESTINATION_CHANNEL, DELAY_BETWEEN_ADDS, MAX_RETRY_ATTEMPTS

class TelegramMigrator:
    def __init__(self):
        self.client = TelegramClient("session_file", API_ID, API_HASH)
        self.added_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    async def start(self):
        """Client ko connect karo"""
        await self.client.start(PHONE_NUMBER)
        print("\n✓ Telegram se connect ho gaya!\n")

    async def get_members(self):
        """Source group se sab members nikalo"""
        print(f"📥 Group '{SOURCE_GROUP}' se members nikale ja rahe hain...\n")
        members = []
        
        try:
            async for member in self.client.get_participants(SOURCE_GROUP):
                if member.deleted:  # Deleted accounts ko skip karo
                    self.skipped_count += 1
                    continue
                members.append(member)
                print(f"   → {member.first_name} (@{member.username or 'No username'})")
            
            print(f"\n✓ Total members found: {len(members)}\n")
            return members
        except ChannelPrivateError:
            print(f"❌ Error: '{SOURCE_GROUP}' private hai ya access nahi hai!")
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

    async def add_member(self, channel, member):
        """Ek member ko channel mein add karo"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                await self.client.edit_permissions(channel, member, view_messages=True)
                return True, None
            except UserPrivacyRestrictedError:
                return False, "Privacy settings (user ne allow nahi kiya)"
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(1)
                    continue
                return False, str(e)
        return False, "Max retries exceeded"

    async def migrate(self):
        """Sab members ko channel mein add karo"""
        members = await self.get_members()
        
        if not members:
            print("❌ Koi members nahi mile!")
            return
        
        print(f"\n📤 Channel '{DESTINATION_CHANNEL}' mein members add ho rahe hain...\n")
        print("=" * 60)
        
        for i, member in enumerate(members, 1):
            name = member.first_name or "Unknown"
            username = member.username or "No username"
            
            success, error = await self.add_member(DESTINATION_CHANNEL, member)
            
            if success:
                self.added_count += 1
                status = "✓ Added"
                print(f"[{i}/{len(members)}] {status:15} → {name} (@{username})")
            else:
                self.failed_count += 1
                status = f"✗ Failed"
                print(f"[{i}/{len(members)}] {status:15} → {name} (@{username}) - {error}")
            
            # Rate limiting - Telegram ke rules ko follow karne ke liye
            await asyncio.sleep(DELAY_BETWEEN_ADDS)
        
        print("=" * 60)
        self.print_summary()

    def print_summary(self):
        """Final summary dikha do"""
        total = self.added_count + self.failed_count + self.skipped_count
        print(f"\n📊 MIGRATION SUMMARY:")
        print(f"   ✓ Successfully added: {self.added_count}")
        print(f"   ✗ Failed: {self.failed_count}")
        print(f"   ⊘ Skipped (deleted accounts): {self.skipped_count}")
        print(f"   Total processed: {total}\n")

    async def close(self):
        """Connection band karo"""
        await self.client.disconnect()
        print("✓ Disconnect ho gaya!\n")

async def main():
    print("\n" + "="*60)
    print("   🚀 TELEGRAM MEMBER MIGRATOR 🚀")
    print("   Group se Channel mein members add karne ka tool")
    print("="*60)
    
    migrator = TelegramMigrator()
    
    try:
        await migrator.start()
        await migrator.migrate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await migrator.close()

if __name__ == "__main__":
    asyncio.run(main())
