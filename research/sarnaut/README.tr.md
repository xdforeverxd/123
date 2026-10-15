# Allods 3.0–4.0 → Godot → Android: teknik inceleme

İnceleme: 15 Ekim 2026. İncelenen kaynak commitleri upstream-lock.json içindedir.
Bu klasör bir Allods oyunu veya çalışan Android portu değildir. Yerel uyumluluk
incelemesinin ilk aracını ve uygulanabilir geliştirme sırasını içerir.
Mevcut Aetheria APK'ları bu araştırmanın sonucu değildir.

## Karar

Hedef eski Allods davranışını korumaksa yeni temel SarnautCore/client + server
olmalı; VoidQuest farklı bir oyun için uygun başlangıçtı. Ancak SarnautCore henüz
tam oyun değildir ve 3.0/4.0 destekli uçtan uca dönüştürme zinciri doğrulanmadı.

Üç ayrı problem var: veri tabanını okumak, görsel/harita/animasyonu Godot'a
dönüştürmek ve oyun kurallarını yeniden uygulamak. Birinin başarısı diğerlerini
kanıtlamaz. Eski istemci kurulumu sunucu mantığının tamamını sağlamaz.

## Kodda doğrulanan durum

| Bileşen | Mevcut uygulama | Sınır |
|---|---|---|
| Godot istemcisi | C#, üçüncü şahıs SpringArm kamera, yürüme/uçuş, yerel harita inceleme | Çevrimdışı walkabout, tam çevrimdışı RPG değildir |
| Haritalar | Terrain sahneleri, OBJ yedeği, MapRegion JSON yerleşimleri, malzeme ve ışık yükleme | Hazır dönüştürülmüş yerel dosyalara bağımlı; klasik 1.1 varsayılanları var |
| Karakterler | Dönüştürülmüş rig/geoset yükleme, idle/run geçişleri, NPC görselleri | Eksik modeller kapsül olarak gösterilebilir; bunu başarı saymamalıyız |
| Oturum | HTTP hesap/karakter akışı, tek kullanımlık shard bileti, pack kimliği | Çalışan auth ve shard gerekir |
| Ağ | QUIC akışı, protobuf, authoritative konum, snapshot interpolation | GameSession doğrudan System.Net.Quic'e bağlı; Android taşıması doğrulanmamış |
| Savaş | Go UseAbility doğrulaması, menzil/cooldown/hasar, AI/aggro/leash/respawn kodu | Godot diliminde tek başlangıç yeteneği; eski sınıfların tamamı uygulanmış değil |
| Ganimet/çanta | Sunucu loot ve inventory modülleri, Godot bag/loot view-model'leri | Tam ekipman, görsel kuşanma, ticaret ve ilerleme eşitliği doğrulanmadı |
| Görev | Sunucuda görev durumları ve ödüller, istemcide diyalog/log/tracker | Özel script hedefleri eksik; tüm eski görevler çalışmıyor |
| Kalıcılık | PostgreSQL karakter kaydı, oturum/ödül testleri | Valkey ve NATS da normal servis açılışında gerekli |
| Mobil | InputMap eylemleri yeniden kullanılabilir | Dokunmatik kontrol ve test edilmiş APK/export hattı doğrulanmadı |

Kaynaklar:
- https://github.com/SarnautCore/client
- https://github.com/SarnautCore/server
- https://github.com/SarnautCore/docs/blob/main/adr/0035-m3-league-tutorial.md

ADR 0035, M2'yi küçük bir dilim olarak tanımlıyor ve 1.1 tutorial görevlerinin
21'inden 12'sinin o ölçümde servis edilebildiğini, 9'unun atlandığını belirtiyor.
Bu belge gelecekteki işi de tarif eder; bu sayılar 3.0/4.0 başarı oranı değildir.
Test dosyalarının varlığı bu oturumda testlerin çalıştırıldığı anlamına gelmez.

## 3.0/4.0 dosyaları okunabilir mi?

AllodsOnlineEditorTools GameVersion.cs şu veri tabanı kimliklerini açıkça tanıyor:

| Dönem | Veri tabanı hash'i | Struct namespace |
|---|---|---|
| 3.0.0.x | 2060B40B8CBE5B8D | V3_0_00_89 |
| 4.0.02.4x | 641AD1D48E1FD7EC | V4_0_02_43 |

Bu destek bütün 3.x/4.x yamalarına genellenemez. Yerel pack.bin kimliği ölçülmeli.
Araç BIN/PAK veri tabanlarını XDB/JDB'ye çıkarıyor, metadata listeliyor ve
doku dışa aktarma komutları içeriyor. Godot/Blender eklentileri README'de
planlanmış; tam Godot harita ve animasyon dönüştürücüsü diye sunulmamalı.

--as sürümler arası alan/enum eşleştirmesidir. Uyumsuz alanların veya kaynakların
atlanması mümkün; tam sürüm dönüşümü veya mekanik eşitliği değildir. İlk deneyde
--as kullanmadan özgün modelle ve --strict ile hata kapsamı ölçülmeli.

Kaynak:
https://github.com/paulus-allods/AllodsOnlineEditorTools/blob/main/ClientResources/Structs/GameVersion.cs

## Dönüştürücü erişimi gerçek bir engel

SarnautCore belgeleri ao-godot-converter ve ao-blender-converter isimlerini
veriyor; bu incelemede SarnautCore altındaki iki GitHub uç noktası 404 döndü ve
açık depo araması sonuç vermedi. Gizli, taşınmış veya kaldırılmış olabilirler.
Kaynaklarını, gerçek lisanslarını, 3.0/4.0 profillerini veya derlenebilirliklerini
doğrulayamadık. Belgede Apache-2.0 yazması erişilemeyen kodu denetlemek değildir.

SarnautCore/tools açık, ancak sarnaut-assets (içerik adresli depo),
sarnaut-extract (XDB → YAML), sarnaut-pack (YAML → runtime pack) ve quest census
araçlarını içeriyor. Bunlar eksik görsel dönüştürücünün yerine geçmiyor.
Örneklerin çoğu 1.1 sunucu XDB ağacını kullanıyor. Sadece istemci BIN çıkarmakla
bütün bu sunucu verilerinin elde edileceği varsayılmamalı.

## Yerel ilk deney

Gerekenler: Python 3.10+, EditorTools için .NET 10 SDK. Godot istemcisinin
incelenen csproj'u Godot.NET.Sdk/4.7.2 ve net10.0 istiyor. Motor, SDK ve export
template birlikte sabitlenmeli; eski Aetheria 4.6.3 ayarları buraya taşınmamalı.

1. Sahip olduğun kurulumun kopyasını ve çıktıları Git deposunun DIŞINDA tut.
2. EditorTools'u upstream-lock.json'daki committen indir. Projenin README'sine
   göre solution yerine EditorCLI/EditorCLI.csproj'u Release olarak derle.
3. Aşağıdaki komutlarla yerel sürümü ve okuma hatalarını ölç. Araç yolu,
   Bin yolu ve çıktı yolu örnektir; gerçek klasörlerini seç.

PowerShell örneği:

    dotnet build EditorCLI/EditorCLI.csproj -c Release
    dotnet run --project EditorCLI/EditorCLI.csproj -c Release -- info versions
    dotnet run --project EditorCLI/EditorCLI.csproj -c Release -- pack info "D:\AllodsLocal\Bin" pack.bin
    dotnet run --project EditorCLI/EditorCLI.csproj -c Release -- pack unpack "D:\AllodsLocal\Bin" --strict --dry-run
    dotnet run --project EditorCLI/EditorCLI.csproj -c Release -- pack unpack "D:\AllodsLocal\Bin" -o "D:\AllodsPrivate\xdb" -f Xdb --strict

Dry-run başarı vermeden son komuta geçme. Strict hata çıkarsa önce tür ve alan
uyumsuzluğunu kaydet; sessizce alan atlayarak başarı ilan etme. Yalnızca bu
veri tabanı için gereken kaynaklara sahip ol; yetkisiz sunucu dökümleri edinme.

Bu klasördeki yerel sayım aracı oyun dosyalarını değiştirmez ve ağ bağlantısı
kurmaz. Ham içerik, dosya adları ve mutlak yollar rapora kopyalanmaz.
XDB tür ve görev-hedef sayımları opsiyoneldir. Raporu yine yerel tut.

    python research/sarnaut/audit_local.py --source "D:\AllodsPrivate\xdb" --inspect-xdb --client "D:\Sarnaut\client" --out "D:\AllodsPrivate\audit-01.json"

--converted ile varsa dönüştürücü çıktı ağacı da sayılabilir. Her çalıştırmada
yeni rapor adı kullan; araç dosyanın üstüne yazmaz. Kaynak veya bu depo içine
rapor yazmayı reddeder. Bilgisayarındaki veriyi bu oturumda okuyamadık.

## Android geliştirme sırası ve çıkış koşulları

1. **Veri uyumluluğu:** gerçek 3.0/4.0 hash tanınmalı; strict unpack hataları
   sınıflandırılmalı. Çıkış: tekrarlanabilir yerel envanter ve örnek dönüşüm.
2. **Görsel köprü:** dönüştürücü erişimini çöz veya MIT EditorTools çıktısından
   ayrı bir açık dönüştürücü geliştir. Önce bir statik model+doku, sonra bir
   iskelet/idle/run, son olarak bir terrain tile+collision+yerleşim. Çıkış:
   Godot'ta doğru ölçek/UV/kemik/koordinat, eksik referans raporu.
3. **İçerik sürümü:** classic-1.1 sabitlerini bir ruleset/profile haline getir.
   3.0/4.0 yetenek, stat, görev ve eşya farklarını ayrı veri paketiyle tanımla.
   Client dosyalarında olmayan formülleri kaynağı belli deneylerle yeniden yaz.
4. **Yerel görsel deneme:** ConvertedRoot taşınabilir olsun. Bilgisayardaki
   mutlak res:// yollarını temizle. Telefon içeriği user:// altında kullanıcı
   seçimiyle alsın; Android Storage Access Framework URI'leri normal dosya yolu
   değildir, kopyalama/köprü gerekir. PC'de import edilmiş resource pack ile
   ham OBJ/TRES dosyalarını telefonda yüklemek aynı şey değildir; runtime loader
   ve import bağımlılıkları gerçek export üzerinde sınanmalı.
5. **Dokunmatik:** sol çoklu dokunma joystick'i InputMap hareketine bağla; sağ
   sürüklemeyi kamera için ayrı parmak kimliğiyle işle; hedef, etkileşim,
   zıplama, yetenek, çanta ve görev düğmelerini mevcut view-model'e bağla.
   WalkaboutController fare motion'ını doğrudan işler, bu nedenle yalnızca
   fare emülasyonu yeterli değil. Odak/pause sırasında basılı eylemleri bırak.
6. **Performans:** Forward+ yerine Mobile/Compatibility seçeneklerini ölç;
   terrain shader'larını doğrula, texture mipmap/ETC2-ASTC, LOD, chunk yükleme,
   görünür NPC/ışık sayısı ve çarpışma maliyetini sınırla. Başlangıç kabulü:
   hedef telefonda ölçülmüş 30 FPS ve ısınma/bellek testi.
7. **Oynanabilirlik:** walkabout'a bakarak offline savaş/görev var deneme.
   İlk gerçek oyun döngüsü için PC'de mevcut Go servisleri + sentetik pack kullan.
   Telefonda tam offline oyun ayrı bir yerel simülasyon/persistence işi; mevcut
   PostgreSQL/Valkey/NATS sunucusunu Android'e gömmek ilk tercih değil.
8. **Ağ:** System.Net.Quic bağımlılığını taşıma arayüzü arkasına al. Android için
   önce mevcut protobuf zarfını taşıyan WSS/TLS adaptörü ve Go tarafında eşini
   prototiple. QUIC dinleyicisi WebSocket kabul etmez: iki taraf değişmeli.
   20 Hz hareketi ve biriken snapshot gecikmesini ölç. Alternatif native QUIC
   Android binding'i daha fazla native paketleme/bakım gerektirir.
9. **APK:** uyumlu .NET Godot editor+Android template, SDK/JDK, arm64, debug
   imza ile önce sentetik içerikli boş kabuğu derle. Sonra yerel içerik yükleme,
   hareket/kamera, suspend/resume, geri düğmesi, depolama ve ağ testleri.
   APK export başarısı oynanış veya gerçek cihaz testi yerine geçmez.

Microsoft Android'i bu ağ yolunun test matrisi olarak belgelemiyor; MsQuic
elle derleme olasılığı, mevcut System.Net.Quic kodunun Android'de hazır olduğu
anlamına gelmez:
https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/quic/quic-overview

## Lisans ve dağıtım sınırı

- SarnautCore client/server: AGPL-3.0. Değiştirilmiş sürüm dağıtımında ve AGPL'nin
  kapsadığı ağ kullanımında karşılık gelen kaynak sunma yükümlülükleri incelenmeli.
- SarnautCore/tools: Apache-2.0. EditorTools: MIT.
- SarnautCore/docs: CC-BY-4.0. Dönüştürücüler için belirtilen lisans henüz
  kaynak dosyaları üzerinden doğrulanmadı.
- Bu kod lisansları Allods harita/model/animasyon/metin/müzik/veri tasarımı veya
  marka haklarını devretmez. Yerel kopyaya sahip olmak uyarlama/dağıtım izni değildir;
  yerel kullanımın da sözleşme ve uygulanabilir hukuka uygunluğu ayrıca belirlenmeli.
- Kamuya açık Git/CI/APK yalnızca özgün veya dağıtım izni doğrulanmış sentetik
  içerik taşımalı. Yerel oyun dosyaları ve bunlardan türeyen kaynak/paketler
  GitHub'a veya CI artifact'lerine gönderilmemeli. Gitignore tek başına güvence değildir.
- İnceleme aracı yeni yazılmış MIT lisanslı kod; upstream kod kopyalanmadı.

## Bu çalışmada doğrulama

Bulut yürütme ortamı connector_failed hatasıyla açılamadı. Yerel Godot, .NET,
dönüştürme ve APK testleri yapılmadı. Sentetik Python testleri için ayrı GitHub
Actions işi eklendi. CI sonucu ayrıca raporlanır; CI oyun verisi indirmez.
