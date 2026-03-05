import logging
import asyncio
import random
import time
import httpx
from faker import Faker
from app.core.config import config
from app.modules.tempmail.temply_viewmodel import temply_viewmodel
from app.modules.tempmail.temply_tracker import temply_tracker
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore
from app.core.proxy_loader import load_proxies

logger = logging.getLogger("superlive.modules.gift.orchestrator")
fake = Faker('en_IN')  # Use Indian locale for names

class GiftOrchestrator:
    def __init__(self):
        self.is_active = False
        self.current_task = None

    async def process_single_account(self, livestream_id, worker_index, proxy_url=None):
        """
        Executes a single account lifecycle for the auto-gift loop in 2.0.
        """
        worker_display_id = worker_index + 1
        logger.info(f"\n➡️ [Worker {worker_display_id}] Starting cycle")
        
        try:
            # --- 1. Register Device ---
            try:
                device_res = await SuperliveService.register_device(proxy_url=proxy_url)
                session = {
                    "guid": device_res["upstream_response"]["guid"],
                    "profile": device_res["device_profile"],
                    "domain_config": device_res["domain_config"]
                }
                origin = session["domain_config"]["origin"]
                logger.info(f"📱 [Worker {worker_display_id}] Device registered on {origin}")
            except Exception as e:
                logger.warning(f"⚠️ [Worker {worker_display_id}] Device Reg Failed: {e}")
                return

            # --- 2. Temp Mail ---
            username = temply_tracker.generate_username()
            tm_domain = "temp.ly"
            email = f"{username}@{tm_domain}"
            
            # --- 3. Initial Sign Up (Expects OTP requirement) ---
            try:
                # We EXPECT this to bounce with "Email address has not been verified"
                await SuperliveService.signup_email(
                    email=email,
                    password=email,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
            except Exception as e:
                pass
                
            # --- 4. Request OTP ---
            try:
                otp_req = await SuperliveService.request_email_otp(
                    email=email,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
                
                upstream_data = otp_req.get("upstream_response", {})
                
                # Check for rate limit error
                if "error" in upstream_data:
                    err_msg = upstream_data["error"].get("message", "Unknown Error")
                    logger.warning(f"⚠️ [Worker {worker_display_id}] Stopped: {err_msg}")
                    return
                
                # It might be in data wrapper or straight in the response depending on upstream
                email_verification_id = upstream_data.get("email_verification_id") or upstream_data.get("data", {}).get("email_verification_id")
                
                if not email_verification_id:
                    logger.warning(f"⚠️ [Worker {worker_display_id}] Missing email_verification_id in response")
                    return
                    
                logger.info(f"📧 [Worker {worker_display_id}] OTP Requested for {email} (ID: {email_verification_id})")
            except Exception as e:
                logger.warning(f"⚠️ [Worker {worker_display_id}] Stopped (OTP Request Failed): {e}")
                return

            # --- 5. Fetch OTP from Inbox ---
            otp = None
            poll_start = time.time()
            while time.time() - poll_start < 45:
                if not self.is_active: return
                try:
                    poll_resp = await temply_viewmodel.get_inbox(username, tm_domain, proxy_url=proxy_url)
                    inbox_data = poll_resp.json()
                    otp = temply_viewmodel.extract_otp(inbox_data)
                    if otp:
                        break
                except Exception as e:
                    pass
                await asyncio.sleep(4)
                
            if not otp:
                logger.warning(f"⚠️ [Worker {worker_display_id}] OTP Timeout (No email received)")
                return
                
            logger.info(f"🔑 [Worker {worker_display_id}] OTP Retrieved: {otp}")
            
            # --- 6. Verify OTP ---
            try:
                await SuperliveService.verify_email_otp(
                    verification_id=email_verification_id,
                    code=int(otp),
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
            except Exception as e:
                logger.warning(f"⚠️ [Worker {worker_display_id}] OTP Verification Failed: {e}")
                return

            # --- 7. Final Signup (Get Token) ---
            try:
                signup_res = await SuperliveService.signup_email(
                    email=email,
                    password=email,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
                auth_token = signup_res.get("upstream_response", {}).get("token")
                if not auth_token:
                    raise Exception("No token received after verification")
                
                logger.info(f"\n✅ [Worker {worker_display_id}] Signup Success")
                # Store in local session store
                SessionStore.ACTIVE_USERS[auth_token] = session
            except Exception as e:
                logger.warning(f"⚠️ [Worker {worker_display_id}] Final Signup Failed.")
                return

            # --- 8 & 9. Update Profile Name and Complete ---
            try:
                name = fake.name()
                # Initial update normally hit here in the manual flow
                await SuperliveService.update_profile(
                    update_data={"name": name},
                    auth_token=auth_token,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
                
                # Complete profile with Gender/Bday
                gender = random.choice([0, 1])  # Assuming 0/1 are standard gender ints
                bday = fake.date_of_birth(minimum_age=18, maximum_age=40).strftime("%Y-%m-%d")
                
                await SuperliveService.complete_profile(
                    name=name,
                    gender=gender,
                    birthday=bday,
                    auth_token=auth_token,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
                logger.info(f"👤 [Worker {worker_display_id}] Profile Completed: {name}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️ [Worker {worker_display_id}] Profile Update Failed: {e}")

            # --- 10. Send 4 Gifts in a Loop ---
            target_id = random.choice(livestream_id) if isinstance(livestream_id, list) else livestream_id
            
            import uuid
            
            for g_idx in range(4):
                if not self.is_active: return
                try:
                    await SuperliveService.send_gift(
                        livestream_id=target_id,
                        gift_id=5141, # Rose
                        user_ids=[],
                        guids=[str(uuid.uuid4())],
                        auth_token=auth_token,
                        device_profile=session["profile"],
                        domain_config=session["domain_config"],
                        device_guid=session["guid"],
                        proxy_url=proxy_url
                    )
                    logger.info(f"🎁 [Worker {worker_display_id}] Gift {g_idx+1}/4 Sent to {target_id}")
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception as e:
                    logger.error(f"⚠️ [Worker {worker_display_id}] Gift {g_idx+1} Failed: {e}")

            # --- 11. Logout ---
            try:
                await SuperliveService.logout(
                    auth_token=auth_token,
                    device_profile=session["profile"],
                    domain_config=session["domain_config"],
                    device_guid=session["guid"],
                    proxy_url=proxy_url
                )
                if auth_token in SessionStore.ACTIVE_USERS:
                    del SessionStore.ACTIVE_USERS[auth_token]
                logger.info(f"👋 [Worker {worker_display_id}] Logged out successfully.")
            except:
                pass

        except Exception as e:
            logger.error(f"❌ [Worker {worker_display_id}] Account Process Error: {e}")


    async def run_auto_gift_loop(self, livestream_id, worker_count=2, use_proxy=True, proxies=None):
        """
        Batched Cycle Orchestrator.
        """
        if use_proxy:
            all_proxies = proxies if proxies else []
            if not all_proxies:
                all_proxies = load_proxies()
                if all_proxies:
                    logger.info(f"Loaded {len(all_proxies)} working proxies from proxy.txt.")
            if not all_proxies:
                logger.warning("No proxies available but use_proxy=True! Falling back to single local worker.")
                all_proxies = [None]
        else:
            all_proxies = [None] * worker_count

        logger.info(f"🚀 Starting Auto Gift Loop. Batch Size: {worker_count}. Use Proxy: {use_proxy}")

        cycle_count = 0 
        
        while self.is_active:
            cycle_count += 1
            logger.info(f"\n🔄 === Starting Cycle {cycle_count} ===")
            
            total_proxies = len(all_proxies)
            num_batches = (total_proxies + worker_count - 1) // worker_count
            if num_batches < 1: num_batches = 1
            
            for i in range(0, total_proxies, worker_count):
                if not self.is_active: break
                
                batch_proxies = all_proxies[i : i + worker_count]
                
                tasks = []
                for idx, proxy in enumerate(batch_proxies):
                    current_proxy = proxy if use_proxy else None
                    tasks.append(
                        self.process_single_account(
                            livestream_id=livestream_id,
                            worker_index=i + idx,
                            proxy_url=current_proxy
                        )
                    )
                
                await asyncio.gather(*tasks)
                logger.info(f"✅ Batch {i//worker_count + 1} Completed. Sleeping 5s.")
                await asyncio.sleep(5 + random.uniform(0, 2))
                
            logger.info(f"🏁 Cycle {cycle_count} Finished. Restarting...")
            await asyncio.sleep(2) 


    def start_loop(self, livestream_id, worker_count, use_proxy, proxies=None):
        if self.is_active:
            return False, "Loop is already running"
            
        self.is_active = True
        self.current_task = asyncio.create_task(
            self.run_auto_gift_loop(livestream_id, worker_count, use_proxy, proxies)
        )
        return True, "Loop started"

    def stop_loop(self):
        self.is_active = False
        return True, "Stopping auto gift loop received"

gift_orchestrator = GiftOrchestrator()
