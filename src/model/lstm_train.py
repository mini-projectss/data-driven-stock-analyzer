# src/model/lstm_train.py

import os
import numpy as np
import joblib
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
import tensorflow as tf

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
MODEL_DIR = os.path.join(BASE_DIR, "models", "lstm_ohlc")
os.makedirs(MODEL_DIR, exist_ok=True)

def build_model(input_shape):
    """Builds and compiles the LSTM model for OHLC prediction."""
    model = Sequential([
        Input(shape=input_shape),
        LSTM(units=50, return_sequences=True),
        Dropout(0.2),
        LSTM(units=50),
        Dropout(0.2),
        Dense(units=4)  # 4 outputs for OHLC
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")
    return model

def train_model(stock_name, market_type):
    """Loads sequences, trains the model, and saves it."""
    # This path is now built using the exact stock name from the list
    sequence_path = os.path.join(SEQUENCE_DIR, market_type, stock_name)
    
    if not os.path.exists(sequence_path):
        print(f"❌ Sequence data not found for {stock_name} ({market_type}), skipping...")
        return

    try:
        X = np.load(os.path.join(sequence_path, "X.npy"))
        y = np.load(os.path.join(sequence_path, "y.npy"))

        # Split data (chronologically)
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        model = build_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Train model
        model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=0)
        
        # Evaluate performance
        loss = model.evaluate(X_test, y_test, verbose=0)
        print(f"✅ Trained {stock_name.upper()} ({market_type.upper()}). Test Loss: {loss:.4f}")

        # Save model
        model_path = os.path.join(MODEL_DIR, market_type, stock_name)
        os.makedirs(model_path, exist_ok=True)
        model.save(os.path.join(model_path, "lstm_ohlc_model.keras"))
    
    except MemoryError:
        print(f"⚠️ Insufficient memory to train {stock_name} ({market_type}). Skipping...")
    except Exception as e:
        print(f"❌ Error training {stock_name} ({market_type}): {e}")

if __name__ == "__main__":
    # Your list of remaining stocks
    remaining_stocks = [
        "HCLTECH.BO", "HDFCAMC.BO", "HDFCBANK.BO", "HDFCLIFE.BO", "HEG.BO",
        "HEROMOTOCO.BO", "HFCL.BO", "HINDALCO.BO", "HINDCOPPER.BO", "HINDPETRO.BO",
        "HINDUNILVR.BO", "HINDZINC.BO", "HOMEFIRST.BO", "HONASA.BO", "HONAUT.BO",
        "HSCL.BO", "HUDCO.BO", "HYUNDAI.BO", "ICICIBANK.BO", "ICICIGI.BO",
        "ICICIPRULI.BO", "IDBI.BO", "IDEA.BO", "IDFCFIRSTB.BO", "IEX.BO",
        "IFCI.BO", "IGIL.BO", "IGL.BO", "IIFL.BO", "IKS.BO", "INDGN.BO",
        "INDHOTEL.BO", "INDIACEM.BO", "INDIAMART.BO", "INDIANB.BO", "INDIGO.BO",
        "INDUSINDBK.BO", "INDUSTOWER.BO", "INFY.BO", "INOXINDIA.BO", "INOXWIND.BO",
        "INTELLECT.BO", "IOB.BO", "IOC.BO", "IPCALAB.BO", "IRB.BO", "IRCON.BO",
        "IRCTC.BO", "IREDA.BO", "IRFC.BO", "ITC.BO", "ITI.BO", "J&KBANK.BO",
        "JBCHEPHARM.BO", "JBMA.BO", "JINDALSAW.BO", "JINDALSTEL.BO", "JIOFIN.BO",
        "JKCEMENT.BO", "JKTYRE.BO", "JMFINANCIL.BO", "JPPOWER.BO", "JSL.BO",
        "JSWENERGY.BO", "JSWHL.BO", "JSWINFRA.BO", "JSWSTEEL.BO", "JUBLFOOD.BO",
        "JUBLINGREA.BO", "JUBLPHARMA.BO", "JUSTDIAL.BO", "JWL.BO", "JYOTHYLAB.BO",
        "JYOTICNC.BO", "KAJARIACER.BO", "KALYANKJIL.BO", "KANSAINER.BO", "KARURVYSYA.BO",
        "KAYNES.BO", "KEC.BO", "KEI.BO", "KFINTECH.BO", "KIMS.BO", "KIRLOSBROS.BO",
        "KIRLOSENG.BO", "KNRCON.BO", "KOTAKBANK.BO", "KPIL.BO", "KPITTECH.BO",
        "KPRMILL.BO", "LALPATHLAB.BO", "LATENTVIEW.BO", "LAURUSLABS.BO", "LEMONTREE.BO",
        "LICHSGFIN.BO", "LICI.BO", "LINDEINDIA.BO", "LLOYDSME.BO", "LODHA.BO",
        "LT.BO", "LTF.BO", "LTFOODS.BO", "LTIM.BO", "LTTS.BO", "LUPIN.BO",
        "M&M.BO", "M&MFIN.BO", "MAHABANK.BO", "MAHSEAMLES.BO", "MANAPPURAM.BO",
        "MANKIND.BO", "MANYAVAR.BO", "MAPMYINDIA.BO", "MARICO.BO", "MARUTI.BO",
        "MASTEK.BO", "MAXHEALTH.BO", "MAZDOCK.BO", "MCX.BO", "MEDANTA.BO",
        "METROPOLIS.BO", "MFSL.BO", "MGL.BO", "MINDACORP.BO", "MMTC.BO",
        "MOTHERSON.BO", "MOTILALOFS.BO", "MPHASIS.BO", "MRF.BO", "MRPL.BO",
        "MSUMI.BO", "MUTHOOTFIN.BO", "NAM-INDIA.BO", "NATCOPHARM.BO", "NATIONALUM.BO",
        "NAUKRI.BO", "NAVA.BO", "NAVINFLUOR.BO", "NBCC.BO", "NCC.BO",
        "NESTLEIND.BO", "NETWEB.BO", "NETWORK18.BO", "NEULANDLAB.BO", "NEWGEN.BO",
        "NH.BO", "NHPC.BO", "NIACL.BO", "NIVABUPA.BO", "NLCINDIA.BO",
        "NMDC.BO", "NSLNISP.BO", "NTPC.BO", "NTPCGREEN.BO", "NUVAMA.BO",
        "NYKAA.BO", "OBEROIRLTY.BO", "OFSS.BO", "OIL.BO", "OLAELEC.BO",
        "OLECTRA.BO", "ONGC.BO", "PAGEIND.BO", "PATANJALI.BO", "PAYTM.BO",
        "PCBL.BO", "PEL.BO", "PERSISTENT.BO", "PETRONET.BO", "PFC.BO",
        "PFIZER.BO", "PGEL.BO", "PHOENIXLTD.BO", "PIDILITIND.BO", "PIIND.BO",
        "PNB.BO", "PNBHOUSING.BO", "PNCINFRA.BO", "POLICYBZR.BO", "POLYCAB.BO",
        "POLYMED.BO", "POONAWALLA.BO", "POWERGRID.BO", "POWERINDIA.BO", "PPLPHARMA.BO",
        "PRAJIND.BO", "PREMIERENE.BO", "PRESTIGE.BO", "PTCIL.BO", "PVRINOX.BO",
        "RADICO.BO", "RAILTEL.BO", "RAINBOW.BO", "RAMCOCEM.BO", "RAYMOND.BO",
        "RAYMONDLSL.BO", "RBLBANK.BO", "RCF.BO", "RECLTD.BO", "REDINGTON.BO",
        "RELIANCE.BO", "RENUKA.BO", "RHIM.BO", "RITES.BO", "RKFORGE.BO",
        "ROUTE.BO", "RPOWER.BO", "RRKABEL.BO", "RTNINDIA.BO", "RVNL.BO",
        "SAGILITY.BO", "SAIL.BO", "SAILIFE.BO", "SAMMAANCAP.BO", "SAPPHIRE.BO",
        "SARDAEN.BO", "SAREGAMA.BO", "SBFC.BO", "SBICARD.BO", "SBILIFE.BO",
        "SBIN.BO", "SCHAEFFLER.BO", "SCHNEIDER.BO", "SCI.BO", "SHREECEM.BO",
        "SHRIRAMFIN.BO", "SHYAMMETL.BO", "SIEMENS.BO", "SIGNATURE.BO", "SJVN.BO",
        "SKFINDIA.BO", "SOBHA.BO", "SOLARINDS.BO", "SONACOMS.BO", "SONATSOFTW.BO",
        "SRF.BO", "STARHEALTH.BO", "SUMICHEM.BO", "SUNDARMFIN.BO", "SUNDRMFAST.BO",
        "SUNPHARMA.BO", "SUNTV.BO", "SUPREMEIND.BO", "SUZLON.BO", "SWANENERGY.BO",
        "SWIGGY.BO", "SWSOLAR.BO", "SYNGENE.BO", "SYRMA.BO", "TANLA.BO",
        "TARIL.BO", "TATACHEM.BO", "TATACOMM.BO", "TATACONSUM.BO", "TATAELXSI.BO",
        "TATAINVEST.BO", "TATAMOTORS.BO", "TATAPOWER.BO", "TATASTEEL.BO", "TATATECH.BO",
        "TBOTEK.BO", "TCS.BO", "TECHM.BO", "TECHNOE.BO", "TEJASNET.BO",
        "THERMAX.BO", "TIINDIA.BO", "TIMKEN.BO", "TITAGARH.BO", "TITAN.BO",
        "TORNTPHARM.BO", "TORNTPOWER.BO", "TRENT.BO", "TRIDENT.BO", "TRITURBINE.BO",
        "TRIVENI.BO", "TTML.BO", "TVSMOTOR.BO", "UBL.BO", "UCOBANK.BO",
        "ULTRACEMCO.BO", "UNIONBANK.BO", "UNITDSPR.BO", "UNOMINDA.BO", "UPL.BO",
        "USHAMART.BO", "UTIAMC.BO", "VBL.BO", "VEDL.BO", "VGUARD.BO",
        "VIJAYA.BO", "VMM.BO", "VOLTAS.BO", "VTL.BO", "WAAREEENER.BO",
        "WELCORP.BO", "WELSPUNLIV.BO", "WESTLIFE.BO", "WHIRLPOOL.BO", "WIPRO.BO",
        "WOCKPHARMA.BO", "YESBANK.BO", "ZEEL.BO", "ZENSARTECH.BO", "ZENTEC.BO",
        "ZFCVINDIA.BO", "ZYDUSLIFE.BO"
    ]
    
    for stock_code in remaining_stocks:
        # Correctly formats the stock name to match your folder structure
        stock_name = stock_code.replace('.BO', '_BO')
        market_type = "bse"
        
        train_model(stock_name, market_type)
        
    print("✅ Training completed for all remaining stocks.")