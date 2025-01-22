import pandas as pd

def trading_strategy(data):
    """
    Generates BUY and SELL signals for TRUMP/USDC based on MA5, MA20, VWAP, and volume.

    Parameters:
        data (pd.DataFrame): Trading data containing columns 'Close', 'MA5', 'MA20', 'VWAP', 'Volume', and 'Time'.

    Returns:
        pd.DataFrame: Data with 'Signal' column added, containing BUY, SELL, or HOLD.
    """
    signals = []

    for i in range(len(data)):
        if i < 20:  # Skip rows without sufficient MA20 data
            signals.append("HOLD")
            continue

        row = data.iloc[i]

        # Conditions for BUY
        if row['Close'] < row['VWAP'] and row['Close'] < row['MA20'] and row['Volume'] > data['Volume'].mean():
            signals.append("BUY")

        # Conditions for SELL
        elif row['Close'] > row['MA5'] and row['Close'] > row['VWAP'] and row['Volume'] > data['Volume'].mean():
            signals.append("SELL")

        # Hold in all other cases
        else:
            signals.append("HOLD")

    # Add signals to the DataFrame
    data['Signal'] = signals
    return data

# Example Usage
if __name__ == "__main__":
    # Simulated input data (replace this with actual trading data)
    data = pd.DataFrame({
        'Time': ['2025-01-22 00:01', '2025-01-22 00:02', '2025-01-22 00:03'],
        'Close': [41.5, 42.0, 41.7],
        'MA5': [41.4, 41.6, 41.8],
        'MA20': [41.3, 41.5, 41.7],
        'VWAP': [41.35, 41.55, 41.65],
        'Volume': [1000, 1200, 900],
    })

    data = trading_strategy(data)
    print(data)
