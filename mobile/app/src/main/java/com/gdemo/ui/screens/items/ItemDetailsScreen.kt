package com.gdemo.ui.screens.items

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import coil.decode.VideoFrameDecoder
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.LocationDto
import com.gdemo.data.model.MediaDto
import com.gdemo.data.model.MediaUploadResponse
import com.gdemo.data.model.UpdateItemRequest
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import com.gdemo.util.UploadQueue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.delay
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.source
import java.io.File
import java.io.IOException

@Suppress("DEPRECATION")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ItemDetailsScreen(
    itemId: String,
    paddingValues: PaddingValues,
    onDeleted: () -> Unit,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    val baseUrl = remember { stored.baseUrl }
    val scopeSelection = remember { if (stored.scope.isBlank()) "private" else stored.scope }
    val api = remember { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl)) }

    var title by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }
    var statusExpanded by remember { mutableStateOf(false) }
    val statusOptions = listOf("ok", "new", "broken", "needs_review", "lost", "repaired", "sold", "discarded", "want", "in_transit")
    var message by remember { mutableStateOf("Загружаем карточку...") }
    var mediaList by remember { mutableStateOf<List<MediaDto>>(emptyList()) }
    var locations by remember { mutableStateOf<List<LocationDto>>(emptyList()) }
    var selectedLocationIds by remember { mutableStateOf<List<Int>>(emptyList()) }
    var showLocationDialog by remember { mutableStateOf(false) }
    var newLocationName by remember { mutableStateOf("") }
    var newLocationParent by remember { mutableStateOf("") }
    var tagsList by remember { mutableStateOf<List<String>>(emptyList()) }
    var newTag by remember { mutableStateOf("") }
    var attributesMap by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var attrKey by remember { mutableStateOf("") }
    var attrValue by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var purchaseDate by remember { mutableStateOf("") }
    var linksText by remember { mutableStateOf("") }
    var store by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var currency by remember { mutableStateOf("RUB") }
    var warrantyUntil by remember { mutableStateOf("") }
    var expirationDate by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var manufacturer by remember { mutableStateOf("") }
    var originCountry by remember { mutableStateOf("") }
    var isUploading by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()
    val uploadQueue = remember { UploadQueue(coroutineScope) }
    val queueTasks by uploadQueue.tasks.collectAsState()
    val hasActiveUploads = queueTasks.any { it.status == UploadQueue.Status.PENDING || it.status == UploadQueue.Status.RUNNING || it.status == UploadQueue.Status.RETRYING }
    LaunchedEffect(hasActiveUploads) {
        isUploading = hasActiveUploads
    }
    val idInt = itemId.toIntOrNull() ?: 0

    suspend fun loadItem() {
        try {
            val item = api.getItem(idInt)
            title = item.title
            status = item.status
            tagsList = item.tags
            attributesMap = item.attributes
                ?.filterKeys { it != "links" }
                ?.mapValues { it.value?.toString() ?: "" }
                ?: emptyMap()
            description = item.description.orEmpty()
            purchaseDate = item.purchase_date.orEmpty()
            store = item.store.orEmpty()
            price = item.price?.toString().orEmpty()
            currency = item.currency.orEmpty().ifBlank { "RUB" }
            warrantyUntil = item.warranty_until.orEmpty()
            expirationDate = item.expiration_date.orEmpty()
            quantity = item.quantity?.toString().orEmpty()
            manufacturer = item.manufacturer.orEmpty()
            originCountry = item.origin_country.orEmpty()
            selectedLocationIds = item.location_ids ?: emptyList()
            val linksFromAttrs = (item.attributes?.get("links") as? List<*>)?.mapNotNull { it?.toString() }.orEmpty()
            val linksSource = item.links?.takeIf { it.isNotEmpty() } ?: linksFromAttrs
            linksText = linksSource.joinToString("\n")
            message = "Карточка загружена"
        } catch (e: Exception) {
            message = "Ошибка загрузки: ${e.localizedMessage}"
        }
    }

    suspend fun loadMedia() {
        try {
            mediaList = api.itemMedia(idInt)
        } catch (e: Exception) {
            message = "Медиа не загрузились: ${e.localizedMessage}"
        }
    }

    fun saveItem() {
        coroutineScope.launch {
            try {
                val linksList = linksText.lines().mapNotNull { it.trim().takeIf { it.isNotEmpty() } }
                val attrsClean = attributesMap.filterKeys { it != "links" }
                val attrsWithLinks = if (linksList.isNotEmpty()) attrsClean + ("links" to linksList) else attrsClean
                api.updateItem(
                    idInt,
                    UpdateItemRequest(
                        title = title,
                        status = status,
                        description = description,
                        purchase_date = purchaseDate.ifBlank { null },
                        purchase_datetime = purchaseDate.ifBlank { null },
                        store = store.ifBlank { null },
                        price = price.toDoubleOrNull(),
                        currency = currency.ifBlank { null },
                        warranty_until = warrantyUntil.ifBlank { null },
                        expiration_date = expirationDate.ifBlank { null },
                        quantity = quantity.toIntOrNull(),
                        manufacturer = manufacturer.ifBlank { null },
                        origin_country = originCountry.ifBlank { null },
                        location_ids = selectedLocationIds.ifEmpty { null },
                        location_id = selectedLocationIds.firstOrNull(),
                        tags = tagsList,
                        attributes = attrsWithLinks.ifEmpty { null },
                        links = linksList
                    )
                )
                message = "Сохранено"
                loadItem()
            } catch (e: Exception) {
                message = "Ошибка сохранения: ${e.localizedMessage}"
            }
        }
    }

    fun deleteItem() {
        coroutineScope.launch {
            try {
                val response = api.deleteItem(idInt)
                if (response.isSuccessful) {
                    message = "Удалено"
                    onDeleted()
                } else {
                    message = "Ошибка удаления: ${response.code()}"
                }
            } catch (e: Exception) {
                message = "Ошибка удаления: ${e.localizedMessage}"
            }
        }
    }

    fun attachMedia(uri: Uri, mediaType: String, source: String = "gallery") {
        uploadQueue.enqueue("item_${idInt}_$mediaType") {
            val uploaded = uploadUri(
                context = context,
                uri = uri,
                api = api,
                scope = scopeSelection,
                mediaType = mediaType,
                itemId = idInt,
                source = source
            )
            if (uploaded != null) {
                loadMedia()
                message = "DoDæD'D,Dø D¨¥?D,D§¥?DæD¨D¯DæD«D_"
                true
            } else {
                message = "D?Dæ ¥ŸD'DøD¯D_¥?¥O DúDøD3¥?¥ŸDúD,¥,¥O ¥,DøD1D¯"
                false
            }
        }
    }

    fun unlinkMedia(mediaId: Int, deleteFile: Boolean) {
        coroutineScope.launch {
            try {
                api.unlinkMedia(idInt, mediaId, deleteFile)
                mediaList = mediaList.filterNot { it.id == mediaId }
                message = "Медиа удалено"
            } catch (e: Exception) {
                message = "Ошибка удаления медиа: ${e.localizedMessage}"
            }
        }
    }

    fun createLocation() {
        coroutineScope.launch {
            try {
                val parentId = newLocationParent.toIntOrNull()
                val created = api.createLocation(
                    com.gdemo.data.model.LocationCreateRequest(
                        name = newLocationName,
                        workspace_id = 2,
                        kind = "other",
                        parent_id = parentId
                    )
                )
                locations = locations + created
                newLocationName = ""
                newLocationParent = ""
                message = "Место добавлено"
            } catch (e: Exception) {
                message = "Ошибка создания места: ${e.localizedMessage}"
            }
        }
    }

    fun deleteLocation(id: Int) {
        coroutineScope.launch {
            try {
                api.deleteLocation(id)
                locations = locations.filterNot { it.id == id }
                selectedLocationIds = selectedLocationIds.filterNot { it == id }
                message = "Место удалено"
            } catch (e: Exception) {
                message = "Ошибка удаления места: ${e.localizedMessage}"
            }
        }
    }

    var tempPhotoUri by remember { mutableStateOf<Uri?>(null) }
    var tempVideoUri by remember { mutableStateOf<Uri?>(null) }

    val capturePhotoLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
            if (success) {
                tempPhotoUri?.let { attachMedia(it, "photo", "camera") }
            } else {
                tempPhotoUri = null
            }
        }
    val captureVideoLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.CaptureVideo()) { success ->
            if (success) {
                tempVideoUri?.let { attachMedia(it, "video", "camera") }
            } else {
                tempVideoUri = null
            }
        }

    val pickImageLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) attachMedia(uri, "photo")
        }
    val pickVideoLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) attachMedia(uri, "video")
        }

    LaunchedEffect(Unit) {
        try {
            locations = api.locations()
        } catch (_: Exception) {
        }
    }

    LaunchedEffect(idInt) {
        loadItem()
        loadMedia()
    }

    LaunchedEffect(mediaList.map { it.id to (it.analysis?.status ?: it.detection?.status) }) {
        mediaList
            .filter {
                val analysisStatus = it.analysis?.status ?: it.detection?.status
                analysisStatus == "pending" || analysisStatus == "in_progress"
            }
            .forEach { media ->
                delay(2000)
                runCatching { api.mediaDetails(media.id) }
                    .onSuccess { updated ->
                        mediaList = mediaList.map { current -> if (current.id == updated.id) updated else current }
                    }
            }
    }

    Column(
        modifier = Modifier
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = onBack) { Text("Назад") }
                    Text(text = "Карточка #$itemId")
                }
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Название") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Описание / заметки") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = purchaseDate,
                    onValueChange = { purchaseDate = it },
                    label = { Text("Дата/время покупки (ISO)") },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        val now = LocalDate.now()
                        DatePickerDialog(context, { _, y, m, d ->
                            val date = LocalDate.of(y, m + 1, d)
                            purchaseDate = date.toString()
                        }, now.year, now.monthValue - 1, now.dayOfMonth).show()
                    }) { Text("Выбрать дату") }
                    Button(onClick = {
                        val now = LocalDateTime.now()
                        TimePickerDialog(context, { _, h, min ->
                            val base = if (purchaseDate.isNotBlank()) purchaseDate else LocalDate.now().toString()
                            val dt = LocalDateTime.parse(base + "T00:00:00").withHour(h).withMinute(min)
                            purchaseDate = dt.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
                        }, now.hour, now.minute, true).show()
                    }) { Text("Время") }
                }
                OutlinedTextField(
                    value = store,
                    onValueChange = { store = it },
                    label = { Text("Магазин") },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = price,
                        onValueChange = { price = it },
                        label = { Text("Стоимость") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = currency,
                        onValueChange = { currency = it },
                        label = { Text("Валюта") },
                        modifier = Modifier.weight(1f)
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = warrantyUntil,
                        onValueChange = { warrantyUntil = it },
                        label = { Text("Гарантия до") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = expirationDate,
                        onValueChange = { expirationDate = it },
                        label = { Text("Срок годности") },
                        modifier = Modifier.weight(1f)
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = quantity,
                        onValueChange = { quantity = it },
                        label = { Text("Количество") },
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = { showLocationDialog = true }, modifier = Modifier.weight(1f)) {
                        Text("Выбрать места")
                    }
                }
                Text(
                    text = if (selectedLocationIds.isEmpty()) "Места не выбраны"
                    else "Выбрано: " + selectedLocationIds.joinToString(", "),
                    modifier = Modifier.padding(top = 4.dp)
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = manufacturer,
                        onValueChange = { manufacturer = it },
                        label = { Text("Производитель") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = originCountry,
                        onValueChange = { originCountry = it },
                        label = { Text("Страна производителя") },
                        modifier = Modifier.weight(1f)
                    )
                }
                OutlinedTextField(
                    value = linksText,
                    onValueChange = { linksText = it },
                    label = { Text("Ссылки (по одной в строке)") },
                    modifier = Modifier.fillMaxWidth()
                )
                ExposedDropdownMenuBox(
                    expanded = statusExpanded,
                    onExpandedChange = { statusExpanded = !statusExpanded }
                ) {
                    TextField(
                        value = status,
                        onValueChange = { status = it },
                        readOnly = true,
                        label = { Text("Статус") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = statusExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = statusExpanded,
                        onDismissRequest = { statusExpanded = false }
                    ) {
                        statusOptions.forEach { option ->
                            DropdownMenuItem(
                                text = { Text(option) },
                                onClick = {
                                    status = option
                                    statusExpanded = false
                                }
                            )
                        }
                    }
                }
            }
            item {
                Text("Теги")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = newTag,
                        onValueChange = { newTag = it },
                        label = { Text("Новый тег") },
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = {
                        val t = newTag.trim()
                        if (t.isNotEmpty() && !tagsList.contains(t)) {
                            tagsList = tagsList + t
                        }
                        newTag = ""
                    }) { Text("Добавить") }
                }
                if (tagsList.isNotEmpty()) {
                    tagsList.forEach { tag ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(tag, modifier = Modifier.weight(1f))
                            Button(onClick = { tagsList = tagsList.filterNot { it == tag } }) { Text("X") }
                        }
                    }
                } else {
                    Text("Тегов пока нет")
                }
            }
            item {
                Text("Параметры")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = attrKey,
                        onValueChange = { attrKey = it },
                        label = { Text("Ключ") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = attrValue,
                        onValueChange = { attrValue = it },
                        label = { Text("Значение") },
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = {
                        val key = attrKey.trim()
                        if (key.isNotEmpty()) {
                            attributesMap = attributesMap + (key to attrValue)
                        }
                        attrKey = ""
                        attrValue = ""
                    }) { Text("Добавить") }
                }
                if (attributesMap.isNotEmpty()) {
                    attributesMap.forEach { (k, v) ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("$k = $v", modifier = Modifier.weight(1f))
                            Button(onClick = { attributesMap = attributesMap - k }) { Text("X") }
                        }
                    }
                } else {
                    Text("Параметров пока нет")
                }
            }
            item {
                Button(onClick = { saveItem() }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (isUploading) "Загрузка..." else "Сохранить")
                }
                Button(onClick = { deleteItem() }, modifier = Modifier.fillMaxWidth()) {
                    Text("Удалить")
                }
            }
            item {
                Text(text = "Медиафайлы")
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Button(onClick = { pickImageLauncher.launch("image/*") }, modifier = Modifier.weight(1f)) {
                            Text("Прикрепить фото")
                        }
                        Button(onClick = { pickVideoLauncher.launch("video/*") }, modifier = Modifier.weight(1f)) {
                            Text("Прикрепить видео")
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Button(
                            onClick = {
                                val photoFile = File.createTempFile("capture_photo_", ".jpg", context.cacheDir)
                                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", photoFile)
                                tempPhotoUri = uri
                                capturePhotoLauncher.launch(uri)
                            },
                            modifier = Modifier.weight(1f)
                        ) { Text("Снять фото") }
                        Button(
                            onClick = {
                                val videoFile = File.createTempFile("capture_video_", ".mp4", context.cacheDir)
                                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", videoFile)
                                tempVideoUri = uri
                                captureVideoLauncher.launch(uri)
                            },
                            modifier = Modifier.weight(1f)
                        ) { Text("Записать видео") }
                    }
                    if (queueTasks.isNotEmpty()) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("Очередь загрузки")
                            queueTasks.forEach { task ->
                                val statusText = when (task.status) {
                                    com.gdemo.util.UploadQueue.Status.PENDING -> "Ожидание"
                                    com.gdemo.util.UploadQueue.Status.RUNNING -> "Загрузка"
                                    com.gdemo.util.UploadQueue.Status.RETRYING -> "Повтор (${task.attempts})"
                                    com.gdemo.util.UploadQueue.Status.SUCCESS -> "Готово"
                                    com.gdemo.util.UploadQueue.Status.FAILED -> "Ошибка"
                                }
                                Text("${task.label}: $statusText")
                            }
                        }
                    }
                }
            }
            if (mediaList.isEmpty()) {
                item { Text(text = "Пока нет медиа для этой карточки") }
            } else {
                items(mediaList) { media ->
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text(text = "• #${media.id} (${media.mime_type ?: "файл"}): ${media.path}")
                        val sanitized = ApiClient.sanitizeBaseUrl(baseUrl).trimEnd('/')
                        val fullUrl = "$sanitized/${media.file_url.trimStart('/')}"
                        if ((media.mime_type ?: "").startsWith("image")) {
                            AsyncImage(
                                model = fullUrl,
                                contentDescription = null,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(220.dp)
                                    .padding(top = 4.dp)
                            )
                        } else {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 4.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                AsyncImage(
                                    model = ImageRequest.Builder(context)
                                        .data(fullUrl)
                                        .decoderFactory(VideoFrameDecoder.Factory())
                                        .build(),
                                    contentDescription = null,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(220.dp)
                                )
                                Icon(
                                    imageVector = Icons.Default.PlayArrow,
                                    contentDescription = null,
                                    modifier = Modifier
                                        .height(48.dp)
                                )
                            }
                            Button(onClick = {
                                val intent = Intent(Intent.ACTION_VIEW).apply {
                                    setDataAndType(Uri.parse(fullUrl), "video/*")
                                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                }
                                context.startActivity(intent)
                            }) { Text("Смотреть") }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { unlinkMedia(media.id, false) }) { Text("Отвязать") }
                            Button(onClick = { unlinkMedia(media.id, true) }) { Text("Удалить файл") }
                        }
                    }
                }
            }
            item {
                val linkLines = linksText.lines().mapNotNull { it.trim().takeIf { it.isNotEmpty() } }
                if (linkLines.isNotEmpty()) {
                    Text("Ссылки:")
                    linkLines.forEach { link ->
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Link, contentDescription = null)
                            Text(
                                text = link,
                                color = Color(0xFF1565C0),
                                textDecoration = TextDecoration.Underline,
                                modifier = Modifier.clickable {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(link)).apply {
                                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    }
                                    context.startActivity(intent)
                                }
                            )
                        }
                    }
                }
                Text(text = message)
                Spacer(modifier = Modifier.height(12.dp))
            }
        }
    }

    if (showLocationDialog) {
        AlertDialog(
            onDismissRequest = { showLocationDialog = false },
            confirmButton = {
                Button(onClick = { showLocationDialog = false }) { Text("Готово") }
            },
            title = { Text("Выбор мест") },
            text = {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(locations) { loc ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Checkbox(
                                checked = selectedLocationIds.contains(loc.id),
                                onCheckedChange = { checked ->
                                    selectedLocationIds = if (checked) {
                                        (selectedLocationIds + loc.id).distinct()
                                    } else {
                                        selectedLocationIds.filterNot { it == loc.id }
                                    }
                                }
                            )
                            Text("${loc.id}: ${loc.name}")
                            Button(onClick = { deleteLocation(loc.id) }) { Text("X") }
                        }
                    }
                    item {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Новое место")
                        OutlinedTextField(
                            value = newLocationName,
                            onValueChange = { newLocationName = it },
                            label = { Text("Название") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = newLocationParent,
                            onValueChange = { newLocationParent = it },
                            label = { Text("Parent ID (опционально)") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        Button(onClick = { createLocation() }, modifier = Modifier.fillMaxWidth()) {
                            Text("Создать место")
                        }
                    }
                }
            }
        )
    }
}

private suspend fun uploadUri(
    context: Context,
    uri: Uri,
    api: ApiService,
    scope: String,
    mediaType: String,
    itemId: Int?,
    source: String
): MediaUploadResponse? {
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
            val fileName = (if (itemId != null && itemId > 0) "item_${itemId}" else "inbox") + "_${mediaType}_${System.currentTimeMillis()}$ext"
            val requestBody: RequestBody = object : RequestBody() {
                override fun contentType() = mime.toMediaType()
                override fun writeTo(sink: okio.BufferedSink) {
                    cr.openInputStream(uri)?.use { input ->
                        input.source().use { sourceStream -> sink.writeAll(sourceStream) }
                    } ?: throw IOException("D?Dæ ¥ŸD'DøD¯D_¥?¥O D_¥,D§¥?¥<¥,¥O ¥,DøD1D¯")
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
                subdir = textBody(if (itemId != null && itemId > 0) "items/$itemId" else "inbox"),
                itemId = itemId?.let { textBody(it.toString()) },
                analyze = textBody("true"),
                source = textBody(source),
                clientCreatedAt = textBody(System.currentTimeMillis().toString()),
                mimeType = textBody(mime)
            )
        } catch (_: Exception) {
            null
        }
    }
}
