import struct

from solana.rpc.api import Client
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.instruction import AccountMeta, Instruction  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore

from spl.token.instructions import (
    CloseAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
)

from bonding_curve import get_bonding_curve, sol_for_tokens, tokens_for_sol
from constants import *
from utils import confirm_txn, get_token_balance

def buy(client: Client, payer_keypair: Keypair, mint_str: str, sol_in: float = 0.01, slippage: int = 5, unit_budget: int = 100_000, unit_price: int = 1_000_000) -> bool:
    try:
        print(f"Starting buy transaction for mint: {mint_str}")

        bonding_curve_data = get_bonding_curve(client, mint_str)
        
        if not bonding_curve_data:
            print("Failed to retrieve bonding curve data.")
            return False

        if bonding_curve_data.complete:
            print("Warning: This token has bonded and is only tradable on PumpSwap.")
            return False

        mint = bonding_curve_data.mint
        bonding_curve = bonding_curve_data.bonding_curve
        associated_bonding_curve = bonding_curve_data.associated_bonding_curve
        user = payer_keypair.pubkey()
        creator = bonding_curve_data.creator
        creator_vault = Pubkey.find_program_address([b'creator-vault', bytes(creator)], PUMP_FUN_PROGRAM)[0]
        user_volume_accumulator = Pubkey.find_program_address([b"user_volume_accumulator", bytes(user)], PUMP_FUN_PROGRAM)[0]
        pump_fee_config_pda  = Pubkey.find_program_address([b"fee_config", bytes(PUMP_FUN_PROGRAM)], FEE_PROGRAM)[0]
                
        print("Fetching or creating associated token account...")
        
        token_account_check = client.get_token_accounts_by_owner(payer_keypair.pubkey(), TokenAccountOpts(mint), Processed)
        
        if token_account_check.value:
            associated_user = token_account_check.value[0].pubkey
            token_account_instruction = None
            print("Existing token account found.")
        else:
            associated_user = get_associated_token_address(user, mint)
            token_account_instruction = create_associated_token_account(user, user, mint)
            print(f"Creating token account : {associated_user}")

        print("Calculating transaction amounts...")
        sol_dec = 1e9
        token_dec = 1e6
        virtual_sol_reserves = bonding_curve_data.virtual_sol_reserves / sol_dec
        virtual_token_reserves = bonding_curve_data.virtual_token_reserves / token_dec
        amount = sol_for_tokens(sol_in, virtual_sol_reserves, virtual_token_reserves)
        amount = int(amount * token_dec)
        
        slippage_adjustment = 1 + (slippage / 100)
        max_sol_cost = int((sol_in * slippage_adjustment) * sol_dec)
        print(f"Amount: {amount} | Max Sol Cost: {max_sol_cost}")

        print("Creating swap instructions...")
        keys = [
            AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=associated_bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=associated_user, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=creator_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=GLOBAL_VOL_ACC, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user_volume_accumulator, is_signer=False, is_writable=True),
            AccountMeta(pubkey=pump_fee_config_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_PROGRAM, is_signer=False, is_writable=False)
        ]

        data = bytearray()
        data.extend(bytes.fromhex("66063d1201daebea"))
        data.extend(struct.pack('<Q', amount))
        data.extend(struct.pack('<Q', max_sol_cost))
        swap_instruction = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)

        instructions = [
            set_compute_unit_limit(unit_budget),
            set_compute_unit_price(unit_price),
        ]
        
        if token_account_instruction:
            instructions.append(token_account_instruction)
        instructions.append(swap_instruction)

        print("Compiling transaction message...")
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True)
        ).value
        print(f"Transaction Signature: {txn_sig}")

        print("Confirming transaction...")
        confirmed = confirm_txn(client, txn_sig)
        
        print(f"Transaction confirmed: {confirmed}")
        return confirmed
    except Exception as e:
        print(f"Error occurred during transaction: {e}")
        return False

def sell(client: Client, payer_keypair: Keypair, mint_str: str, percentage: int = 100, slippage: int = 5, unit_budget: int = 100_000, unit_price: int = 1_000_000) -> bool:
    try:
        print(f"Starting sell transaction for mint: {mint_str}")

        if not (1 <= percentage <= 100):
            print("Percentage must be between 1 and 100.")
            return False

        bonding_curve_data = get_bonding_curve(client, mint_str)
        
        if not bonding_curve_data:
            print("Failed to retrieve bonding curve data.")
            return False

        if bonding_curve_data.complete:
            print("Warning: This token has bonded and is only tradable on PumpSwap.")
            return False

        mint = bonding_curve_data.mint
        bonding_curve = bonding_curve_data.bonding_curve
        associated_bonding_curve = bonding_curve_data.associated_bonding_curve
        user = payer_keypair.pubkey()
        associated_user = get_associated_token_address(user, mint)
        creator = bonding_curve_data.creator
        creator_vault = Pubkey.find_program_address([b'creator-vault', bytes(creator)], PUMP_FUN_PROGRAM)[0]
        pump_fee_config_pda  = Pubkey.find_program_address([b"fee_config", bytes(PUMP_FUN_PROGRAM)], FEE_PROGRAM)[0]
        
        print("Retrieving token balance...")
        token_balance = get_token_balance(client, payer_keypair.pubkey(), mint)
        if token_balance == 0 or token_balance is None:
            print("Token balance is zero. Nothing to sell.")
            return False
        print(f"Token Balance: {token_balance}")
        
        print("Calculating transaction amounts...")
        sol_dec = 1e9
        token_dec = 1e6
        token_balance = token_balance * (percentage / 100)
        amount = int(token_balance * token_dec)
        
        virtual_sol_reserves = bonding_curve_data.virtual_sol_reserves / sol_dec
        virtual_token_reserves = bonding_curve_data.virtual_token_reserves / token_dec
        sol_out = tokens_for_sol(token_balance, virtual_sol_reserves, virtual_token_reserves)
        
        slippage_adjustment = 1 - (slippage / 100)
        min_sol_output = int((sol_out * slippage_adjustment) * sol_dec)
        print(f"Amount: {amount} | Minimum Sol Out: {min_sol_output}")
        
        print("Creating swap instructions...")
        keys = [
            AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=associated_bonding_curve, is_signer=False, is_writable=True),
            AccountMeta(pubkey=associated_user, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=creator_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=EVENT_AUTHORITY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PUMP_FUN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=pump_fee_config_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=FEE_PROGRAM, is_signer=False, is_writable=False)
        ]

        data = bytearray()
        data.extend(bytes.fromhex("33e685a4017f83ad"))
        data.extend(struct.pack('<Q', amount))
        data.extend(struct.pack('<Q', min_sol_output))
        swap_instruction = Instruction(PUMP_FUN_PROGRAM, bytes(data), keys)

        instructions = [
            set_compute_unit_limit(unit_budget),
            set_compute_unit_price(unit_price),
            swap_instruction,
        ]

        if percentage == 100:
            print("Preparing to close token account after swap...")
            close_account_instruction = close_account(CloseAccountParams(TOKEN_PROGRAM, associated_user, user, user))
            instructions.append(close_account_instruction)

        print("Compiling transaction message...")
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )

        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=True)
        ).value
        print(f"Transaction Signature: {txn_sig}")

        print("Confirming transaction...")
        confirmed = confirm_txn(client, txn_sig)
        
        print(f"Transaction confirmed: {confirmed}")
        return confirmed

    except Exception as e:
        print(f"Error occurred during transaction: {e}")
        return False
