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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshots.SnapshotStateList
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
import com.gdemo.data.model.MediaUploadResponse
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import com.gdemo.util.AnalyticsLogger
import com.gdemo.util.UploadQueue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.source
import java.io.File
import java.io.IOException
import kotlin.math.roundToInt

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
    data class UploadHistoryItem(
        val id: Long,
        val label: String,
        val status: UploadQueue.Status,
        val attempts: Int,
        val previewUri: String?,
        val mediaType: String?,
        val mediaId: Int? = null,
        val remoteUrl: String? = null,
        val aiStatus: String? = null,
        val aiLabels: List<String> = emptyList()
    )
    val uploadHistorySaver = listSaver<SnapshotStateList<UploadHistoryItem>, List<String>>(
        save = { list: SnapshotStateList<UploadHistoryItem> ->
            list.map {
                listOf(
                    it.id.toString(),
                    it.label,
                    it.status.name,
                    it.attempts.toString(),
                    it.previewUri ?: "",
                    it.mediaType ?: "",
                    it.mediaId?.toString() ?: "",
                    it.remoteUrl ?: "",
                    it.aiStatus ?: "",
                    it.aiLabels.joinToString("|")
                )
            }
        },
        restore = { saved: List<List<String>> ->
            mutableStateListOf<UploadHistoryItem>().apply {
                saved.forEach { row ->
                    add(
                        UploadHistoryItem(
                            id = row.getOrNull(0)?.toLongOrNull() ?: System.currentTimeMillis(),
                            label = row.getOrNull(1) ?: "",
                            status = row.getOrNull(2)?.let { UploadQueue.Status.valueOf(it) }
                                ?: UploadQueue.Status.PENDING,
                            attempts = row.getOrNull(3)?.toIntOrNull() ?: 0,
                            previewUri = row.getOrNull(4)?.ifBlank { null },
                            mediaType = row.getOrNull(5)?.ifBlank { null },
                            mediaId = row.getOrNull(6)?.toIntOrNull(),
                            remoteUrl = row.getOrNull(7)?.ifBlank { null },
                            aiStatus = row.getOrNull(8)?.ifBlank { null },
                            aiLabels = row.getOrNull(9)?.split("|")?.filter { it.isNotBlank() } ?: emptyList()
                        )
                    )
                }
            }
        }
    )
    val uploadHistory = rememberSaveable(saver = uploadHistorySaver) { mutableStateListOf<UploadHistoryItem>() }
    LaunchedEffect(queueTasks) {
        queueTasks.forEach { task ->
            val idx = uploadHistory.indexOfFirst { it.id == task.id }
            if (idx >= 0) {
                uploadHistory[idx] = uploadHistory[idx].copy(status = task.status, attempts = task.attempts)
            } else {
                uploadHistory.add(
                    UploadHistoryItem(
                        id = task.id,
                        label = task.label,
                        status = task.status,
                        attempts = task.attempts,
                        previewUri = task.previewUri,
                        mediaType = task.mediaType
                    )
                )
            }
        }
    }
    val api = remember(baseUrl) { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl)) }

    LaunchedEffect(baseUrl) {
        runCatching { api.locations() }.onSuccess {
            locations = it
            AnalyticsLogger.debug("locations_loaded", mapOf("count" to it.size))
        }
    }

    fun uploadMedia(uri: Uri, mediaType: String, source: String) {
        val label = "quick_${mediaType}_${System.currentTimeMillis()}"
        uploadQueue.enqueue(
            label = label,
            previewUri = uri.toString(),
            mediaType = mediaType
        ) {
            try {
                val uploaded = uploadQuickMedia(context, api, uri, stored.scope.ifBlank { "private" }, mediaType, source)
                var details = runCatching { api.mediaDetails(uploaded.id) }.getOrNull()
                if (details?.analysis == null && details?.detection == null) {
                    repeat(10) {
                        delay(1500)
                        details = runCatching { api.mediaDetails(uploaded.id) }.getOrNull()
                        if (details?.analysis != null || details?.detection != null) return@repeat
                    }
                }
                val sanitized = ApiClient.sanitizeBaseUrl(baseUrl).trimEnd('/')
                val remoteUrl = details?.file_url?.let { "$sanitized/${it.trimStart('/')}" }
                val aiStatus = details?.analysis?.status ?: details?.detection?.status ?: uploaded.analysis?.status
                val aiLabels = details?.detection?.objects?.take(3)?.map {
                    val conf = (it.confidence * 100).roundToInt()
                    "${it.label} (${conf}%)"
                } ?: emptyList()
                val idx = uploadHistory.indexOfFirst { it.label == label }
                if (idx >= 0) {
                    uploadHistory[idx] = uploadHistory[idx].copy(
                        mediaId = uploaded.id,
                        remoteUrl = remoteUrl,
                        aiStatus = aiStatus,
                        aiLabels = aiLabels
                    )
                } else {
                    uploadHistory.add(
                        UploadHistoryItem(
                            id = System.currentTimeMillis(),
                            label = label,
                            status = UploadQueue.Status.SUCCESS,
                            attempts = 1,
                            previewUri = uri.toString(),
                            mediaType = mediaType,
                            mediaId = uploaded.id,
                            remoteUrl = remoteUrl,
                            aiStatus = aiStatus,
                            aiLabels = aiLabels
                        )
                    )
                }
                message = "Файл отправлен, откройте в AI Review"
                AnalyticsLogger.event("quick_add_media_upload", mapOf("type" to mediaType, "source" to source))
                true
            } catch (e: Exception) {
                message = "Ошибка загрузки: ${e.localizedMessage}"
                AnalyticsLogger.event("quick_add_media_error", mapOf("error" to e.localizedMessage, "type" to mediaType, "source" to source))
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
            uri?.let {
                val mime = context.contentResolver.getType(it) ?: ""
                val mediaType = if (mime.startsWith("video/")) "video" else "photo"
                uploadMedia(it, mediaType, "quick_gallery")
            }
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
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
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
                if (uploadHistory.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("История загрузок")
                        uploadHistory.forEach { task ->
                            val statusText = when (task.status) {
                                UploadQueue.Status.PENDING -> "Ожидание"
                                UploadQueue.Status.RUNNING -> "Загрузка"
                                UploadQueue.Status.RETRYING -> "Повтор (${task.attempts})"
                                UploadQueue.Status.SUCCESS -> "Готово"
                                UploadQueue.Status.FAILED -> "Ошибка"
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text("${task.label}: $statusText")
                                val previewSource = task.remoteUrl ?: task.previewUri
                                previewSource?.let { preview ->
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
                                task.aiStatus?.let { status ->
                                    Text("AI: $status")
                                }
                                if (task.aiLabels.isNotEmpty()) {
                                    Text(task.aiLabels.joinToString())
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
) : MediaUploadResponse {
    return withContext(Dispatchers.IO) {
        val cr = context.contentResolver
        val mime = cr.getType(uri) ?: if (mediaType == "video") "video/mp4" else "image/jpeg"
        AnalyticsLogger.debug("quick_add_media_mime", mapOf("mime" to mime, "mediaType" to mediaType, "source" to source))
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
