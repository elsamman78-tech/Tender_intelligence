# الخطوات التالية لصاحب المشروع — تشغيل 24/7

كل تجهيزات الكود وDocker وGitHub CI وCloud-Init موجودة بالفعل داخل هذا المستودع. المتبقي هو إنشاء السيرفر من حسابك وربط Cloudflare؛ هاتان الخطوتان تتطلبان تسجيل دخول/تحقق شخصي ولا يجب مشاركة كلمات المرور أو مفاتيح SSH أو Tokens داخل GitHub أو ChatGPT.

## A) إنشاء Oracle Cloud VM مجانية

1. افتح Oracle Cloud Free Tier وسجل الدخول أو أنشئ حساباً.
2. اختر Compute → Instances → Create instance.
3. استخدم Ubuntu 24.04 LTS (أو 22.04 LTS).
4. اختر فقط Shape يظهر في Oracle Console أنه Always Free eligible. يفضل Ampere A1 Flex إذا كانت السعة متاحة.
5. ابقِ CPU/RAM وBoot Volume داخل حدود Always Free الظاهرة في حسابك؛ 50 GB Boot Volume كافٍ للاختبار الأول.
6. في Advanced options → Management → Initialization script / Cloud-Init الصق محتوى الملف:
   `cloud-init/oracle-ubuntu.yaml`
7. أضف SSH key بالطريقة التي يوفرها Oracle واحتفظ بالمفتاح الخاص عندك فقط.
8. اضغط Create.

Cloud-Init سيقوم تلقائياً بتثبيت Docker ونسخ المشروع وتشغيله والتحقق من Health endpoint.

بعد دقائق، من SSH أو Oracle Console نفذ:

```bash
sudo cloud-init status --long
cd /opt/Tender_intelligence
sudo docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

## B) ربط Cloudflare Tunnel

1. افتح Cloudflare Dashboard → Zero Trust → Networks → Tunnels.
2. أنشئ Tunnel باسم مثل `tender-intelligence`.
3. انسخ Tunnel token ولا تضعه في GitHub أو المحادثة.
4. على الـVM عدل `/opt/Tender_intelligence/.env` وضع:

```env
CLOUDFLARE_TUNNEL_TOKEN=YOUR_TOKEN_HERE
```

5. شغل:

```bash
cd /opt/Tender_intelligence
./scripts/cloud_start_with_cloudflare.sh
```

6. في Public Hostname اجعل Service:

```text
http://tender-intelligence:8000
```

7. قبل الاستخدام الطبيعي، أضف Cloudflare Access policy تسمح فقط بالمستخدمين/الإيميلات المصرح بها.

## C) اختبار نهائي

- افتح الرابط من الموبايل.
- أغلق كمبيوتر المكتب تماماً.
- تأكد أن Dashboard تعمل.
- افتح `/api/v1/health`.
- شغل Discovery وتأكد من حفظ البيانات بعد إعادة تشغيل الـcontainer.
- نفذ `./scripts/backup.sh` وتأكد من إنشاء Backup.

لا تستخدم أي مورد مدفوع في Oracle أو Cloudflare إذا كان الهدف الالتزام بـ ZERO_COST_MODE.
