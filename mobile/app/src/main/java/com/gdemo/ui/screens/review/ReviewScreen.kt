package com.gdemo.ui.screens.review

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import coil.compose.rememberAsyncImagePainter
import com.gdemo.data.local.connectionPrefs
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.CreateItemRequest
import com.gdemo.data.model.MediaDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.source
import java.io.File
import java.io.IOException

@Composable
fun ReviewScreen(paddingValues: PaddingValues) {
    val context = LocalContext.current
    val prefs = remember { context.connectionPrefs() }
    val stored = remember { context.loadConnection() }
    var baseUrl by remember { mutableStateOf(stored.baseUrl) }
    var scopeSelection by rememberSaveable { mutableStateOf(stored.scope) }
    var statusText by remember { mutableStateOf("Пока ничего не загружено") }
    var recentMedia by remember { mutableStateOf<List<MediaDto>>(emptyList()) }
    var isLoading by remember { mutableStateOf(false) }
    var newItemTitle by rememberSaveable { mutableStateOf("") }
    var newItemStatus by rememberSaveable { mutableStateOf("ok") }
    var newItemLocation by rememberSaveable { mutableStateOf("") }
    var itemCreateResult by remember { mutableStateOf("") }
    var capturePhotoUri by remember { mutableStateOf<Uri?>(null) }
    var captureVideoUri by remember { mutableStateOf<Uri?>(null) }
    var pendingAction by remember { mutableStateOf<(() -> Unit)?>(null) }

    val coroutineScope = rememberCoroutineScope()
    var api: ApiService by remember { mutableStateOf(ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl))) }

    fun reloadConnection() {
        val now = context.loadConnection()
        baseUrl = now.baseUrl
        scopeSelection = now.scope
        api = ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl))
    }

    suspend fun fetchRecent() {
        try {
            isLoading = true
            recentMedia = api.recentMedia(scopeSelection)
            statusText = "Загружено медиа: ${recentMedia.size}"
        } catch (e: Exception) {
            statusText = "Ошибка загрузки списка: ${e.localizedMessage}"
        } finally {
            isLoading = false
        }
    }

    LaunchedEffect(baseUrl, scopeSelection) {
        fetchRecent()
    }

    val permissionLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { perms ->
            val granted = perms.values.all { it }
            if (granted) {
                pendingAction?.invoke()
            } else {
                statusText = "Нужно разрешение на камеру/микрофон"
            }
            pendingAction = null
        }

    val takePhotoLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success && capturePhotoUri != null) {
            coroutineScope.launch {
                val ok = uploadUri(context, capturePhotoUri!!, api, scopeSelection, "photo")
                statusText = if (ok) "Фото загружено" else "Ошибка загрузки фото"
                fetchRecent()
            }
        }
    }
    val captureVideoLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CaptureVideo()) { success ->
        if (success && captureVideoUri != null) {
            coroutineScope.launch {
                val ok = uploadUri(context, captureVideoUri!!, api, scopeSelection, "video")
                statusText = if (ok) "Видео загружено" else "Ошибка загрузки видео"
                fetchRecent()
            }
        }
    }

    val pickImage = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            coroutineScope.launch {
                val ok = uploadUri(context, uri, api, scopeSelection, "photo")
                statusText = if (ok) "Фото загружено" else "Ошибка загрузки фото"
                fetchRecent()
            }
        }
    }
    val pickVideo = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            coroutineScope.launch {
                val ok = uploadUri(context, uri, api, scopeSelection, "video")
                statusText = if (ok) "Видео загружено" else "Ошибка загрузки видео"
                fetchRecent()
            }
        }
    }

    fun ensurePermissions(perms: Array<String>, onReady: () -> Unit) {
        val missing = perms.any { ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED }
        if (missing) {
            pendingAction = onReady
            permissionLauncher.launch(perms)
        } else {
            onReady()
        }
    }

    fun startCameraPhoto() {
        val uri = context.createTempMediaUri(".jpg")
        capturePhotoUri = uri
        ensurePermissions(arrayOf(Manifest.permission.CAMERA)) { takePhotoLauncher.launch(uri) }
    }

    fun startCameraVideo() {
        val uri = context.createTempMediaUri(".mp4")
        captureVideoUri = uri
        ensurePermissions(arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)) {
            captureVideoLauncher.launch(uri)
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Медиа и AI-обработка", fontWeight = FontWeight.Bold)
            Text(if (statusText.isNotBlank()) statusText else "Статус неизвестен")
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { reloadConnection() }) { Text("Обновить подключение") }
                Button(onClick = { coroutineScope.launch { fetchRecent() } }) { Text("Обновить список") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = {
                    scopeSelection = "public"
                    prefs.edit().putString("scope", "public").apply()
                    coroutineScope.launch { fetchRecent() }
                }) { Text("Публичные") }
                Button(onClick = {
                    scopeSelection = "private"
                    prefs.edit().putString("scope", "private").apply()
                    coroutineScope.launch { fetchRecent() }
                }) { Text("Приватные") }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { pickImage.launch("image/*") }, modifier = Modifier.weight(1f)) { Text("Выбрать фото") }
                Button(onClick = { pickVideo.launch("video/*") }, modifier = Modifier.weight(1f)) { Text("Выбрать видео") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { startCameraPhoto() }, modifier = Modifier.weight(1f)) { Text("Снять фото") }
                Button(onClick = { startCameraVideo() }, modifier = Modifier.weight(1f)) { Text("Записать видео") }
            }
        }
        item {
            Text("Быстрое создание карточки", fontWeight = FontWeight.Bold)
            OutlinedTextField(
                value = newItemTitle,
                onValueChange = { newItemTitle = it },
                label = { Text("Название") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = newItemStatus,
                onValueChange = { newItemStatus = it },
                label = { Text("Статус (ok/new/broken/needs_review)") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = newItemLocation,
                onValueChange = { newItemLocation = it },
                label = { Text("Местоположение (опционально)") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(4.dp))
            Button(
                onClick = {
                    coroutineScope.launch {
                        try {
                            isLoading = true
                            val created = api.createItem(
                                CreateItemRequest(
                                    title = newItemTitle,
                                    status = statusToEnum(newItemStatus),
                                    workspace_id = 2,
                                    description = null,
                                    category = null,
                                    location_id = null,
                                    scope = scopeSelection
                                )
                            )
                            itemCreateResult = "Карточка создана id=${created.id}"
                            newItemTitle = ""
                        } catch (e: Exception) {
                            itemCreateResult = "Не удалось создать: ${e.localizedMessage}"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (isLoading) "Создаю..." else "Создать карточку")
            }
            if (itemCreateResult.isNotBlank()) {
                Text(itemCreateResult)
            }
        }
        if (recentMedia.isNotEmpty()) {
            item { Text("Последние медиа", fontWeight = FontWeight.Bold) }
        }
        items(recentMedia) { media ->
            MediaCard(media = media, baseUrl = baseUrl)
        }
    }
}

private fun statusToEnum(human: String): String =
    when (human.lowercase()) {
        "в порядке", "ok" -> "ok"
        "новый", "new" -> "new"
        "сломан", "broken" -> "broken"
        "потерян", "lost" -> "lost"
        "отремонтирован", "repaired" -> "repaired"
        "продан", "sold" -> "sold"
        "выкинут", "discarded" -> "discarded"
        "хочу купить", "want" -> "want"
        "в пути", "in_transit" -> "in_transit"
        "надо проверить", "needs_review" -> "needs_review"
        else -> "ok"
    }

private suspend fun uploadUri(
    context: Context,
    uri: Uri,
    api: ApiService,
    scope: String,
    mediaType: String
): Boolean {
    return withContext(Dispatchers.IO) {
        try {
            val cr = context.contentResolver
            val mime = cr.getType(uri)
                ?: if (mediaType == "video") "video/mp4" else "image/jpeg"
            val ext = when {
                mime.contains("jpeg") || mime.contains("jpg") -> ".jpg"
                mime.contains("png") -> ".png"
                mime.contains("heic") -> ".heic"
                mime.contains("mp4") || mime.contains("video") -> ".mp4"
                else -> ""
            }
            val fileName = "mobile_${mediaType}_${System.currentTimeMillis()}$ext"
            val requestBody: RequestBody = object : RequestBody() {
                override fun contentType() = mime.toMediaType()
                override fun writeTo(sink: okio.BufferedSink) {
                    cr.openInputStream(uri)?.use { input ->
                        input.source().use { source -> sink.writeAll(source) }
                    } ?: throw IOException("Не удалось открыть файл")
                }
            }
            val part = MultipartBody.Part.createFormData("file", fileName, requestBody)
            val textBody: (String) -> RequestBody = { it.toRequestBody("text/plain".toMediaType()) }
            api.uploadMedia(
                file = part,
                workspaceId = textBody("2"),
                ownerUserId = textBody("1"),
                mediaType = textBody(mediaType),
                scope = textBody(scope),
                subdir = textBody("mobile"),
                analyze = textBody("true"),
                source = textBody("review"),
                clientCreatedAt = textBody(System.currentTimeMillis().toString()),
                mimeType = textBody(mime)
            )
            true
        } catch (_: Exception) {
            false
        }
    }
}

@Composable
private fun MediaCard(media: MediaDto, baseUrl: String) {
    val fullUrl = remember(baseUrl, media.file_url) {
        val sanitized = ApiClient.sanitizeBaseUrl(baseUrl).trimEnd('/')
        val relative = media.file_url.trimStart('/')
        "$sanitized/$relative"
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors()
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(text = "ID: ${media.id}")
            Text(text = "Путь: ${media.path}")
            Text(text = "AI статус: ${media.detection?.status ?: "pending"}")
            if (media.mime_type?.startsWith("image") == true) {
                Image(
                    painter = rememberAsyncImagePainter(fullUrl),
                    contentDescription = null,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                )
            } else {
                Text(text = "Файл: $fullUrl")
            }
            media.detection?.objects?.let { objects ->
                if (objects.isNotEmpty()) {
                    Text("Найдено объектов:")
                    objects.forEach { obj ->
                        Text("- ${obj.label} (${String.format("%.2f", obj.confidence)})")
                    }
                } else {
                    Text("Объекты не найдены")
                }
            } ?: Text("AI обработка в очереди...")
        }
    }
}

private fun Context.createTempMediaUri(suffix: String): Uri {
    val dir = File(cacheDir, "captures").apply { mkdirs() }
    val file = File.createTempFile("capture_", suffix, dir)
    return FileProvider.getUriForFile(this, "${packageName}.fileprovider", file)
}
