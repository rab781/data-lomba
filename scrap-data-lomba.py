import requests
import time
import pandas as pd

# Menambahkan User-Agent agar tidak diblokir
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

semua_data = []
page = 1
total_page = 1 # Kita set 1 dulu, nanti akan diperbarui saat mengambil halaman 1

print("Memulai proses ekstraksi data SIMT...")

while page <= total_page:
    url = f"https://simt.kemendikdasmen.go.id/api/v2/list-kurasi?page={page}&per_page=10"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data_json = response.json()
            
            # 1. Update total_page jika ini adalah halaman pertama
            if page == 1:
                total_page = data_json.get('result', {}).get('pagination', {}).get('total_page', 1)
                total_data = data_json.get('result', {}).get('pagination', {}).get('total_data', 0)
                print(f"Ditemukan total {total_page} halaman dan {total_data} data.")
            
            # 2. Ambil isi datanya dari result -> list
            items = data_json.get('result', {}).get('list', [])
            
            if not items:
                print(f"Halaman {page} kosong, menghentikan proses.")
                break
                
            semua_data.extend(items)
            print(f"Berhasil mengambil {len(items)} data dari halaman {page}/{total_page}")
            
        else:
            print(f"Gagal mengambil halaman {page}. Status Code: {response.status_code}")
            
        # Jeda 2 detik agar server pemerintah tidak tumbang / memblokir IP kita
        time.sleep(2)
        page += 1
        
    except Exception as e:
        print(f"Terjadi error pada halaman {page}: {e}")
        break # Hentikan jika terjadi error jaringan yang parah

# Jadikan DataFrame Pandas dan simpan ke CSV
print("Menyimpan data...")
df = pd.DataFrame(semua_data)

# Menyimpan ke format CSV (bisa dibuka di Excel)
df.to_csv('data_kurasi_simt.csv', index=False, encoding='utf-8')
print("Selesai! Data berhasil disimpan ke 'data_kurasi_simt.csv'")