# Configuration Guide - Testnet & Mainnet Support

## Overview

ICT AutoTrader supports both Binance **Testnet** (safe testing environment) and **Mainnet** (real trading) environments. This guide explains how to properly configure each environment.

## Environment Configuration Files

### 1. `.env` File (API Credentials)

The `.env` file stores your Binance API credentials. **NEVER commit this file to version control** - it's already in `.gitignore`.

#### Setup Instructions:

```bash
# Copy the example file to create your .env
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

#### Required Environment Variables:

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `BINANCE_TESTNET_API_KEY` | Testnet API Key | https://testnet.binance.vision/ |
| `BINANCE_TESTNET_API_SECRET` | Testnet API Secret | https://testnet.binance.vision/ |
| `BINANCE_MAINNET_API_KEY` | **Mainnet API Key** | https://www.binance.com/en/my/settings/api-management |
| `BINANCE_MAINNET_API_SECRET` | **Mainnet API Secret** | https://www.binance.com/en/my/settings/api-management |
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications | Discord Server Settings > Integrations |

### 2. `config.yaml` File (Trading Configuration)

The `config.yaml` file controls which environment to use and sets trading parameters.

#### Critical Setting: `use_testnet`

```yaml
# TESTNET (safe for testing)
use_testnet: true

# MAINNET (REAL money - use with EXTREME caution)
use_testnet: false
```

## Testnet vs Mainnet Comparison

| Feature | Testnet | Mainnet |
|---------|---------|---------|
| **Money at Risk** | ❌ No (fake money) | ✅ Yes (REAL money) |
| **API Endpoint** | `testnet.binance.vision` | `api.binance.com` |
| **Purpose** | Testing & Development | Live Trading |
| **API Keys** | Separate testnet keys | Separate mainnet keys |
| **Risk** | Zero financial risk | **HIGH financial risk** |

## Step-by-Step Setup

### For Testnet (Recommended for Initial Development)

1. **Get Testnet API Keys**
   - Visit https://testnet.binance.vision/
   - Register or login
   - Generate API Key and Secret
   - Save them securely

2. **Configure `.env`**
   ```env
   BINANCE_TESTNET_API_KEY=your_actual_testnet_key_here
   BINANCE_TESTNET_API_SECRET=your_actual_testnet_secret_here
   DISCORD_WEBHOOK_URL=your_webhook_url_here
   ```

3. **Verify `config.yaml`**
   ```yaml
   use_testnet: true  # ✅ Safe mode enabled
   ```

4. **Run the bot** - It will use testnet automatically

### For Mainnet (ONLY After Extensive Testing)

⚠️ **WARNING**: Mainnet trading involves REAL money. Proceed ONLY if you:
- ✅ Have tested EXTENSIVELY on testnet
- ✅ Understand all risk parameters
- ✅ Are comfortable with potential losses
- ✅ Have verified all trading logic
- ✅ Have proper monitoring in place

1. **Get Mainnet API Keys**
   - Visit https://www.binance.com/en/my/settings/api-management
   - Create API Key with appropriate permissions:
     - ✅ Enable Reading
     - ✅ Enable Spot & Margin Trading
     - ❌ Disable withdrawals (for safety)
   - Save keys securely

2. **Configure `.env`**
   ```env
   BINANCE_MAINNET_API_KEY=your_actual_mainnet_key_here
   BINANCE_MAINNET_API_SECRET=your_actual_mainnet_secret_here
   ```

3. **Update `config.yaml`**
   ```yaml
   use_testnet: false  # ⚠️  REAL trading enabled

   # Start with CONSERVATIVE parameters
   risk_per_trade: 0.01          # Only 1% risk per trade
   max_daily_loss_percent: 0.02  # Stop after 2% daily loss
   max_position_percent: 0.05    # Small positions only
   ```

4. **Double-Check Everything**
   - Verify risk parameters are appropriate
   - Ensure stop-loss mechanisms are working
   - Test with SMALL amounts first

## How the System Uses These Settings

The trading bot will automatically:

1. **Read `config.yaml`** to check `use_testnet` flag
2. **Load appropriate API keys** from `.env`:
   - If `use_testnet: true` → uses `BINANCE_TESTNET_*` keys
   - If `use_testnet: false` → uses `BINANCE_MAINNET_*` keys
3. **Connect to correct API endpoint**:
   - Testnet: `https://testnet.binance.vision`
   - Mainnet: `https://api.binance.com`

## Safety Checklist Before Going Live

Before setting `use_testnet: false`, ensure:

- [ ] Bot has been tested on testnet for at least 2-4 weeks
- [ ] All risk management parameters are properly configured
- [ ] Stop-loss mechanisms are working correctly
- [ ] Discord notifications are set up and working
- [ ] You understand the trading strategy completely
- [ ] You have a plan for monitoring the bot 24/7
- [ ] You're prepared for potential losses
- [ ] Mainnet API keys have withdrawal disabled
- [ ] You've started with small position sizes

## Testing Configuration

Run the configuration tests to verify setup:

```bash
# Run configuration validation tests
python3 -m pytest tests/test_config.py -v

# All 11 tests should PASS ✅
```

## Common Issues

### Issue: "API key not found"
**Solution**: Ensure you've created `.env` file (not just `.env.example`) and added your actual API keys.

### Issue: "Invalid API signature"
**Solution**:
- Check that API key and secret are correct
- Ensure you're using testnet keys with `use_testnet: true`
- Ensure you're using mainnet keys with `use_testnet: false`

### Issue: "Permission denied"
**Solution**: Check API key permissions on Binance - ensure trading is enabled.

## Security Best Practices

1. **NEVER commit `.env` file** to git (it's in `.gitignore`)
2. **Keep testnet and mainnet keys separate**
3. **Disable withdrawals** on mainnet API keys
4. **Use IP restrictions** on Binance API key settings
5. **Rotate API keys regularly**
6. **Monitor bot activity** constantly when on mainnet
7. **Start small** - test with minimal funds first

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review error messages carefully
- Test on testnet first before reporting mainnet issues
