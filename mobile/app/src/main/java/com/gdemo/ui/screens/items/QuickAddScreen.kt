package com.gdemo.ui.screens.items

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import coil.compose.AsyncImage
import coil.request.ImageRequest
import coil.decode.VideoFrameDecoder
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.CreateItemRequest
import com.gdemo.data.model.LocationDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import com.gdemo.util.AnalyticsLogger
import com.gdemo.util.UploadQueue
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QuickAddScreen(paddingValues: PaddingValues, onItemCreated: (Int) -> Unit = {}) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    var baseUrl by remember { mutableStateOf(stored.baseUrl) }
    var title by remember { mutableStateOf("") }
    var locations by remember { mutableStateOf<List<LocationDto>>(emptyList()) }
    var selectedLocation by remember { mutableStateOf<LocationDto?>(null) }
    var message by remember { mutableStateOf("") }
    var saveAndNext by remember { mutableStateOf(false) }
    var showPicker by remember { mutableStateOf(false) }
    var search by remember { mutableStateOf("") }
    var isUploading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val uploadQueue = remember { UploadQueue(scope) }
    val queueTasks by uploadQueue.tasks.collectAsState()
    val hasActiveUploads = queueTasks.any { it.status == UploadQueue.Status.PENDING || it.status == UploadQueue.Status.RUNNING || it.status == UploadQueue.Status.RETRYING }
    LaunchedEffect(hasActiveUploads) {
        isUploading = hasActiveUploads
    }
    val api = remember(baseUrl) { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl)) }

    LaunchedEffect(baseUrl) {
        runCatching { api.locations() }.onSuccess {
            locations = it
            AnalyticsLogger.debug("locations_loaded", mapOf("count" to it.size))
        }
    }

    fun uploadMedia(uri: Uri, mediaType: String, source: String) {
        uploadQueue.enqueue(
            label = "quick_${mediaType}_${System.currentTimeMillis()}",
            previewUri = uri.toString(),
            mediaType = mediaType
        ) {
            try {
                uploadQuickMedia(context, api, uri, stored.scope.ifBlank { "private" }, mediaType, source)
                message = "Файл отправлен, откройте в AI Review"
                AnalyticsLogger.event("quick_add_media_upload", mapOf("type" to mediaType, "source" to source))
                true
            } catch (e: Exception) {
                message = "Ошибка загрузки: ${e.localizedMessage}"
                AnalyticsLogger.event("quick_add_media_error", mapOf("error" to e.localizedMessage))
                false
            }
        }
    }

    var tempPhotoUri by remember { mutableStateOf<Uri?>(null) }
    var tempVideoUri by remember { mutableStateOf<Uri?>(null) }
    val capturePhotoLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
            if (success) tempPhotoUri?.let { uploadMedia(it, "photo", "quick_camera") } else tempPhotoUri = null
        }
    val captureVideoLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.CaptureVideo()) { success ->
            if (success) tempVideoUri?.let { uploadMedia(it, "video", "quick_camera") } else tempVideoUri = null
        }
    val pickMediaLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            uri?.let { uploadMedia(it, "photo", "quick_gallery") }
        }

    fun save() {
        scope.launch {
            try {
                AnalyticsLogger.event("quick_add_submit", mapOf("location" to selectedLocation?.id))
                val created = api.createItem(
                    CreateItemRequest(
                        title = title,
                        status = "new",
                        workspace_id = 2,
                        location_id = selectedLocation?.id,
                        scope = stored.scope
                    )
                )
                message = "Создано #${created.id}"
                AnalyticsLogger.event("quick_add_success", mapOf("itemId" to created.id))
                onItemCreated(created.id)
                if (saveAndNext) {
                    title = ""
                } else {
                    title = ""
                    selectedLocation = null
                }
            } catch (e: Exception) {
                message = "Ошибка: ${e.localizedMessage}"
                AnalyticsLogger.event("quick_add_error", mapOf("error" to e.localizedMessage))
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Быстрое добавление", style = MaterialTheme.typography.headlineSmall)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Название вещи") }
                )
                OutlinedButton(
                    onClick = {
                        showPicker = true
                        AnalyticsLogger.event("quick_add_open_location_picker")
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(selectedLocation?.path ?: "Выбрать локацию")
                }
                                Text("Мгновенное медиа")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        val photoFile = File.createTempFile("qa_capture_photo_", ".jpg", context.cacheDir)
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", photoFile)
                        tempPhotoUri = uri
                        capturePhotoLauncher.launch(uri)
                    }, modifier = Modifier.weight(1f)) { Text("Снять фото") }
                    Button(onClick = {
                        val videoFile = File.createTempFile("qa_capture_video_", ".mp4", context.cacheDir)
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", videoFile)
                        tempVideoUri = uri
                        captureVideoLauncher.launch(uri)
                    }, modifier = Modifier.weight(1f)) { Text("Записать видео") }
                }
                Button(onClick = { pickMediaLauncher.launch("*/*") }, modifier = Modifier.fillMaxWidth()) {
                    Text("Выбрать из галереи")
                }
                if (queueTasks.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Очередь загрузки")
                        queueTasks.forEach { task ->
                            val statusText = when (task.status) {
                                UploadQueue.Status.PENDING -> "Ожидание"
                                UploadQueue.Status.RUNNING -> "Загрузка"
                                UploadQueue.Status.RETRYING -> "Повтор (${task.attempts})"
                                UploadQueue.Status.SUCCESS -> "Готово"
                                UploadQueue.Status.FAILED -> "Ошибка"
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text("${task.label}: $statusText")
                                task.previewUri?.let { preview ->
                                    val isVideo = (task.mediaType ?: "").contains("video")
                                    val model: Any = if (isVideo) {
                                        ImageRequest.Builder(context)
                                            .data(preview)
                                            .decoderFactory(VideoFrameDecoder.Factory())
                                            .build()
                                    } else preview
                                    AsyncImage(
                                        model = model,
                                        contentDescription = null,
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(140.dp)
                                    )
                                }
                            }
                        }
                    }
                }
Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Checkbox(checked = saveAndNext, onCheckedChange = { saveAndNext = it })
                    Text("Сохранить и добавить следующую")
                }
                Button(
                    onClick = { save() },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = title.isNotBlank()
                ) { Text("Сохранить") }
                if (message.isNotBlank()) {
                    Text(message, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
    if (showPicker) {
        val filtered = locations.filter {
            search.isBlank() || it.name.contains(search, true) || (it.path?.contains(search, true) == true)
        }
        ModalBottomSheet(onDismissRequest = { showPicker = false }) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Выберите локацию", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = search,
                    onValueChange = { search = it },
                    label = { Text("Поиск по названию/пути") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                filtered.forEach { loc ->
                    ListItem(
                        headlineContent = { Text(loc.path ?: loc.name) },
                        supportingContent = { Text(loc.kind ?: "") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                selectedLocation = loc
                                showPicker = false
                                AnalyticsLogger.event("quick_add_location_selected", mapOf("locationId" to loc.id))
                            }
                    )
                }
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

private suspend fun uploadQuickMedia(
    context: android.content.Context,
    api: ApiService,
    uri: Uri,
    scope: String,
    mediaType: String,
    source: String
) {
    withContext(Dispatchers.IO) {
        val cr = context.contentResolver
        val mime = cr.getType(uri) ?: if (mediaType == "video") "video/mp4" else "image/jpeg"
        val ext = when {
            mime.contains("jpeg") || mime.contains("jpg") -> ".jpg"
            mime.contains("png") -> ".png"
            mime.contains("heic") -> ".heic"
            mime.contains("mp4") || mime.contains("video") -> ".mp4"
            else -> ""
        }
        val fileName = "quick_${mediaType}_${System.currentTimeMillis()}$ext"
        val requestBody: RequestBody = object : RequestBody() {
            override fun contentType() = mime.toMediaType()
            override fun writeTo(sink: okio.BufferedSink) {
                cr.openInputStream(uri)?.use { input ->
                    input.source().use { sourceStream -> sink.writeAll(sourceStream) }
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
            subdir = textBody("inbox"),
            analyze = textBody("true"),
            source = textBody(source),
            clientCreatedAt = textBody(System.currentTimeMillis().toString()),
            mimeType = textBody(mime)
        )
    }
}
