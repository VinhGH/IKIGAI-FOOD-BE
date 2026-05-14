# API_CONTRACT_IAM.md
> **Dành cho Frontend team.** File này là nguồn sự thật duy nhất cho IAM API.
> Version: 1.0.0 | Base URL: `https://api.{domain}.com/v1`

---

## Quy ước chung

### Request Headers

```http
Content-Type: application/json
Authorization: Bearer {access_token}   ← bắt buộc với route có 🔒
```

### Response format chuẩn

**Thành công:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Lỗi:**
```json
{
  "success": false,
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "Email này đã được sử dụng"
  }
}
```

### HTTP Status Codes

| Code | Ý nghĩa |
|------|---------|
| 200 | Thành công |
| 201 | Tạo mới thành công |
| 400 | Request không hợp lệ (validation) |
| 401 | Chưa xác thực / token hết hạn |
| 403 | Không có quyền |
| 404 | Không tìm thấy |
| 409 | Conflict (email/phone đã tồn tại) |
| 422 | Business rule violation |
| 500 | Server error |

### Token Strategy

| Token | TTL | Lưu ở đâu |
|-------|-----|-----------|
| Access Token (JWT) | 15 phút | Memory (không localStorage) |
| Refresh Token | 30 ngày | HttpOnly Cookie hoặc SecureStorage (mobile) |

**Flow refresh token:**
1. Gọi bất kỳ API nào → nhận 401
2. Gọi `POST /auth/refresh` với refresh token
3. Nhận access token mới → retry request gốc
4. Nếu refresh cũng 401 → redirect về login

---

## Auth Endpoints

---

### 1. Đăng ký tài khoản

```
POST /auth/register
Auth: ❌ Không cần
```

**Request body:**
```json
{
  "email": "user@example.com",
  "full_name": "Nguyễn Văn A",
  "password": "Abcd@1234",
  "role": "customer",
  "phone": "0901234567"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `email` | string | ✅ | format email hợp lệ |
| `full_name` | string | ✅ | max 100 ký tự, không rỗng |
| `password` | string | ✅ | min 8 ký tự |
| `role` | enum | ✅ | `customer` \| `restaurant_owner` \| `shipper` |
| `phone` | string | ❌ | 10 chữ số, bắt đầu bằng 0 |

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Nguyễn Văn A",
    "role": "customer",
    "is_active": false
  }
}
```

**Lưu ý FE:** `is_active = false` — cần redirect sang màn hình "Kiểm tra email của bạn".

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `EMAIL_ALREADY_EXISTS` | 409 | Email đã được dùng |
| `PHONE_ALREADY_EXISTS` | 409 | Số điện thoại đã được dùng |

---

### 2. Xác thực email

```
POST /auth/verify-email
Auth: ❌ Không cần
```

**Request body:**
```json
{
  "email": "user@example.com",
  "code": "A3F9B2"
}
```

| Field | Type | Required | Ghi chú |
|-------|------|----------|---------|
| `email` | string | ✅ | |
| `code` | string | ✅ | 6 ký tự, gửi qua email |

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Xác thực email thành công. Bạn có thể đăng nhập."
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `USER_NOT_FOUND` | 404 | Email không tồn tại |
| `USER_ALREADY_ACTIVE` | 409 | Tài khoản đã được xác thực trước đó |
| `INVALID_VERIFICATION_CODE` | 400 | Code sai hoặc hết hạn (TTL: 24h) |

---

### 3. Đăng nhập

```
POST /auth/login
Auth: ❌ Không cần
```

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "Abcd@1234"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "Nguyễn Văn A",
      "role": "customer",
      "is_active": true
    }
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | Email hoặc password sai |
| `USER_NOT_ACTIVE` | 403 | Chưa verify email |

---

### 4. Refresh token

```
POST /auth/refresh
Auth: ❌ Không cần (dùng refresh token thay thế)
```

**Request body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `INVALID_TOKEN` | 401 | Token không hợp lệ |
| `TOKEN_EXPIRED` | 401 | Refresh token đã hết hạn → bắt login lại |
| `TOKEN_REVOKED` | 401 | Token đã bị thu hồi (logout thiết bị khác) |

---

### 5. Đăng xuất

```
POST /auth/logout
Auth: 🔒 Bắt buộc
```

**Request body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Đăng xuất thành công"
  }
}
```

**Lưu ý FE:** Sau khi nhận 200, xoá access token khỏi memory ngay.

---

### 6. Quên mật khẩu

```
POST /auth/forgot-password
Auth: ❌ Không cần
```

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Nếu email tồn tại, chúng tôi đã gửi mã OTP."
  }
}
```

**Lưu ý FE:** Response luôn 200 dù email có tồn tại hay không — tránh email enumeration attack. OTP có TTL 15 phút.

---

### 7. Reset mật khẩu

```
POST /auth/reset-password
Auth: ❌ Không cần
```

**Request body:**
```json
{
  "email": "user@example.com",
  "code": "A3F9B2",
  "new_password": "NewPass@5678"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `email` | string | ✅ | |
| `code` | string | ✅ | OTP 6 ký tự |
| `new_password` | string | ✅ | min 8 ký tự |

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại."
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `INVALID_VERIFICATION_CODE` | 400 | OTP sai hoặc hết hạn (TTL: 15 phút) |
| `USER_NOT_FOUND` | 404 | Email không tồn tại |

---

### 8. Đổi mật khẩu

```
PUT /auth/change-password
Auth: 🔒 Bắt buộc
```

**Request body:**
```json
{
  "current_password": "OldPass@1234",
  "new_password": "NewPass@5678"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Đổi mật khẩu thành công"
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | Mật khẩu hiện tại sai |

---

## User Endpoints

---

### 9. Lấy thông tin cá nhân

```
GET /users/me
Auth: 🔒 Bắt buộc
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Nguyễn Văn A",
    "phone": "0901234567",
    "role": "customer",
    "is_active": true,
    "created_at": "2026-01-15T08:00:00Z"
  }
}
```

---

## Address Endpoints
> Chỉ dành cho role `customer`

---

### 10. Lấy danh sách địa chỉ

```
GET /users/me/addresses
Auth: 🔒 Bắt buộc | Role: customer
```

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "address_name": "Nhà riêng",
      "is_default": true,
      "province_code": 48,
      "district_code": 490,
      "ward_code": 20194,
      "address_detail": "123 Nguyễn Văn Linh",
      "full_address": "123 Nguyễn Văn Linh, Phường Hải Châu I, Quận Hải Châu, Đà Nẵng"
    },
    {
      "id": 2,
      "address_name": "Văn phòng",
      "is_default": false,
      "province_code": 48,
      "district_code": 490,
      "ward_code": 20197,
      "address_detail": "456 Lê Duẩn",
      "full_address": "456 Lê Duẩn, Phường Thạch Thang, Quận Hải Châu, Đà Nẵng"
    }
  ]
}
```

---

### 11. Thêm địa chỉ

```
POST /users/me/addresses
Auth: 🔒 Bắt buộc | Role: customer
```

**Request body:**
```json
{
  "address_name": "Nhà riêng",
  "is_default": true,
  "province_code": 48,
  "district_code": 490,
  "ward_code": 20194,
  "address_detail": "123 Nguyễn Văn Linh"
}
```

| Field | Type | Required | Ghi chú |
|-------|------|----------|---------|
| `address_name` | string | ❌ | Default: "Địa chỉ mặc định" |
| `is_default` | boolean | ❌ | Default: false. Nếu true → các địa chỉ khác tự động unset |
| `province_code` | integer | ✅ | Lấy từ Location API |
| `district_code` | integer | ✅ | Lấy từ Location API |
| `ward_code` | integer | ✅ | Lấy từ Location API |
| `address_detail` | string | ✅ | Số nhà, tên đường |

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "address_name": "Nhà riêng",
    "is_default": true,
    "province_code": 48,
    "district_code": 490,
    "ward_code": 20194,
    "address_detail": "123 Nguyễn Văn Linh",
    "full_address": "123 Nguyễn Văn Linh, Phường Hải Châu I, Quận Hải Châu, Đà Nẵng"
  }
}
```

---

### 12. Set địa chỉ mặc định

```
PATCH /users/me/addresses/{address_id}/default
Auth: 🔒 Bắt buộc | Role: customer
```

**Không cần request body.**

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Đã đặt làm địa chỉ mặc định"
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `ADDRESS_NOT_FOUND` | 404 | Address không tồn tại hoặc không thuộc user này |

---

### 13. Xoá địa chỉ

```
DELETE /users/me/addresses/{address_id}
Auth: 🔒 Bắt buộc | Role: customer
```

**Không cần request body.**

**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "Đã xoá địa chỉ"
  }
}
```

**Errors:**
| Code | HTTP | Khi nào |
|------|------|---------|
| `ADDRESS_NOT_FOUND` | 404 | Address không tồn tại hoặc không thuộc user này |

---

## Error Code Reference — IAM Module

| Code | HTTP | Mô tả |
|------|------|-------|
| `EMAIL_ALREADY_EXISTS` | 409 | Email đã được sử dụng |
| `PHONE_ALREADY_EXISTS` | 409 | Số điện thoại đã được sử dụng |
| `USER_NOT_FOUND` | 404 | Không tìm thấy user |
| `USER_ALREADY_ACTIVE` | 409 | Tài khoản đã xác thực rồi |
| `USER_NOT_ACTIVE` | 403 | Chưa xác thực email |
| `INVALID_CREDENTIALS` | 401 | Sai email hoặc password |
| `INVALID_VERIFICATION_CODE` | 400 | Mã OTP sai hoặc hết hạn |
| `INVALID_TOKEN` | 401 | Token không hợp lệ |
| `TOKEN_EXPIRED` | 401 | Token hết hạn |
| `TOKEN_REVOKED` | 401 | Token đã bị thu hồi |
| `ADDRESS_NOT_FOUND` | 404 | Địa chỉ không tồn tại |

---

## Appendix: Enum Values

### `role`
```
customer          → Khách hàng đặt món
restaurant_owner  → Chủ nhà hàng
shipper           → Tài xế giao hàng
admin             → Quản trị viên (không tự đăng ký được)
```

### Datetime format
Tất cả datetime trả về theo chuẩn **ISO 8601 UTC**: `2026-01-15T08:00:00Z`

---

## Changelog

| Version | Date | Thay đổi |
|---------|------|---------|
| 1.0.0 | 2026-05-14 | Initial release — 13 endpoints IAM |
