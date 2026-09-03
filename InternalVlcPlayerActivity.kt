package org.jellyfin.mobile.player.vlc

import android.app.Activity
import android.app.AlertDialog
import android.app.PictureInPictureParams
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import org.jellyfin.mobile.utils.Constants
import org.jellyfin.sdk.api.client.ApiClient
import org.jellyfin.sdk.api.client.extensions.subtitleApi
import org.jellyfin.sdk.api.operations.SubtitleApi
import org.jellyfin.sdk.model.api.RemoteSubtitleInfo
import org.jellyfin.sdk.model.serializer.toUUIDOrNull
import org.koin.core.component.KoinComponent
import org.koin.core.component.inject
import org.videolan.libvlc.LibVLC
import org.videolan.libvlc.Media
import org.videolan.libvlc.MediaPlayer
import org.videolan.libvlc.interfaces.IMedia
import org.videolan.libvlc.util.VLCVideoLayout
import java.io.File
import java.util.Locale

class InternalVlcPlayerActivity :
    AppCompatActivity(),
    KoinComponent {

    private val apiClient: ApiClient by inject()
    private val subtitleApi: SubtitleApi by lazy {
        apiClient.subtitleApi
    }

    private lateinit var libVLC: LibVLC
    private lateinit var mediaPlayer: MediaPlayer
    private lateinit var videoLayout: VLCVideoLayout

    private lateinit var controlsContainer: LinearLayout
    private lateinit var playPause: Button
    private lateinit var seekBar: SeekBar
    private lateinit var positionText: TextView
    private lateinit var titleText: TextView
    private lateinit var speedButton: Button
    private lateinit var aspectButton: Button

    private var startPositionMs = 0L
    private var userSeeking = false
    private var returnedResult = false
    private var controlsVisible = true

    private var speedIndex = 2
    private val speeds = floatArrayOf(
        0.5f,
        0.75f,
        1.0f,
        1.25f,
        1.5f,
        2.0f,
    )

    private var aspectIndex = 0
    private val aspects = arrayOf(
        null,
        "16:9",
        "4:3",
        "1:1",
    )

    private val hideControlsRunnable = Runnable {
        hideControls()
    }

    private val progressUpdater = object : Runnable {
        override fun run() {
            if (
                ::mediaPlayer.isInitialized &&
                !userSeeking
            ) {
                val duration =
                    mediaPlayer.length.coerceAtLeast(0L)

                val position =
                    mediaPlayer.time.coerceAtLeast(0L)

                if (duration > 0L) {
                    seekBar.max = 1000

                    seekBar.progress =
                        (
                            (position * 1000L) /
                                duration
                            )
                            .toInt()
                            .coerceIn(
                                0,
                                1000,
                            )
                }

                positionText.text =
                    "${formatTime(position)} / ${formatTime(duration)}"
            }

            if (::seekBar.isInitialized) {
                seekBar.postDelayed(
                    this,
                    500L,
                )
            }
        }
    }

    override fun onCreate(
        savedInstanceState: Bundle?,
    ) {
        super.onCreate(savedInstanceState)

        window.addFlags(
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        )

        hideSystemUi()

        val mediaUri = intent.data

        if (mediaUri == null) {
            finishWithResult(false)
            return
        }

        startPositionMs =
            intent.getIntExtra(
                "position",
                0,
            )
                .toLong()
                .coerceAtLeast(0L)

        buildUi()

        libVLC = LibVLC(
            this,
            arrayListOf(
                "--audio-time-stretch",
                "--network-caching=1500",
                "--http-reconnect",
            ),
        )

        mediaPlayer =
            MediaPlayer(libVLC)

        mediaPlayer.attachViews(
            videoLayout,
            null,
            false,
            false,
        )

        mediaPlayer.setEventListener { event ->
            runOnUiThread {
                when (event.type) {
                    MediaPlayer.Event.Playing -> {
                        if (
                            startPositionMs > 0L &&
                            mediaPlayer.time < 1000L
                        ) {
                            mediaPlayer.time =
                                startPositionMs
                        }

                        playPause.text = "PAUSE"
                        scheduleControlsHide()
                    }

                    MediaPlayer.Event.Paused -> {
                        playPause.text = "PLAY"
                        showControls()
                    }

                    MediaPlayer.Event.EndReached -> {
                        finishWithResult(true)
                    }

                    MediaPlayer.Event.EncounteredError -> {
                        Toast.makeText(
                            this,
                            "Erro ao reproduzir o vídeo.",
                            Toast.LENGTH_LONG,
                        ).show()

                        finishWithResult(false)
                    }
                }
            }
        }

        val media =
            Media(
                libVLC,
                mediaUri,
            )

        media.setHWDecoderEnabled(
            true,
            false,
        )

        media.addOption(
            ":network-caching=1500"
        )

        media.addOption(
            ":http-reconnect=true"
        )

        addIntentSubtitleSlaves(media)

        mediaPlayer.media = media
        media.release()

        mediaPlayer.play()

        seekBar.post(
            progressUpdater
        )
    }

    private fun addIntentSubtitleSlaves(
        media: Media,
    ) {
        @Suppress("DEPRECATION")
        val subtitleUris =
            intent.getParcelableArrayExtra(
                "subs"
            )
                ?.filterIsInstance<Uri>()
                .orEmpty()

        subtitleUris.forEach { subtitleUri ->
            runCatching {
                media.addSlave(
                    IMedia.Slave(
                        IMedia.Slave.Type.Subtitle,
                        3,
                        subtitleUri.toString(),
                    )
                )
            }
        }

        intent.getStringExtra(
            "subtitles_location"
        )
            ?.takeIf {
                it.isNotBlank()
            }
            ?.let { selectedSubtitle ->
                runCatching {
                    media.addSlave(
                        IMedia.Slave(
                            IMedia.Slave.Type.Subtitle,
                            4,
                            selectedSubtitle,
                        )
                    )
                }
            }
    }

    private fun buildUi() {
        val root =
            FrameLayout(this).apply {
                setBackgroundColor(
                    Color.BLACK
                )
            }

        videoLayout =
            VLCVideoLayout(this).apply {
                setOnClickListener {
                    if (controlsVisible) {
                        hideControls()
                    } else {
                        showControls()
                    }
                }
            }

        root.addView(
            videoLayout,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ),
        )

        controlsContainer =
            LinearLayout(this).apply {
                orientation =
                    LinearLayout.VERTICAL

                setBackgroundColor(
                    0xA0000000.toInt()
                )

                setPadding(
                    16,
                    10,
                    16,
                    10,
                )
            }

        titleText =
            TextView(this).apply {
                setTextColor(
                    Color.WHITE
                )

                textSize = 17f

                text =
                    intent.getStringExtra(
                        "title"
                    )
                        ?: "TARSVideo"

                setPadding(
                    8,
                    0,
                    8,
                    8,
                )
            }

        seekBar =
            SeekBar(this).apply {
                max = 1000

                setOnSeekBarChangeListener(
                    object :
                        SeekBar.OnSeekBarChangeListener {

                        override fun onProgressChanged(
                            seekBar: SeekBar?,
                            progress: Int,
                            fromUser: Boolean,
                        ) = Unit

                        override fun onStartTrackingTouch(
                            seekBar: SeekBar?,
                        ) {
                            userSeeking = true

                            controlsContainer.removeCallbacks(
                                hideControlsRunnable
                            )
                        }

                        override fun onStopTrackingTouch(
                            seekBar: SeekBar?,
                        ) {
                            val duration =
                                mediaPlayer.length

                            if (
                                duration > 0L &&
                                seekBar != null
                            ) {
                                mediaPlayer.time =
                                    (
                                        duration *
                                            seekBar.progress
                                        ) / 1000L
                            }

                            userSeeking = false
                            scheduleControlsHide()
                        }
                    }
                )
            }

        positionText =
            TextView(this).apply {
                setTextColor(
                    Color.WHITE
                )

                text =
                    "00:00 / 00:00"

                gravity =
                    Gravity.END

                setPadding(
                    8,
                    0,
                    8,
                    4,
                )
            }

        val buttonRow =
            LinearLayout(this).apply {
                orientation =
                    LinearLayout.HORIZONTAL

                gravity =
                    Gravity.CENTER_VERTICAL
            }

        val scroll =
            HorizontalScrollView(this).apply {
                isHorizontalScrollBarEnabled =
                    false

                addView(
                    buttonRow,
                    HorizontalScrollView.LayoutParams(
                        HorizontalScrollView.LayoutParams.WRAP_CONTENT,
                        HorizontalScrollView.LayoutParams.WRAP_CONTENT,
                    ),
                )
            }

        val back =
            makeButton(
                "VOLTAR"
            ) {
                finishWithResult(false)
            }

        val rewind =
            makeButton(
                "-10s"
            ) {
                seekBy(
                    -10_000L
                )
            }

        playPause =
            makeButton(
                "PAUSE"
            ) {
                if (mediaPlayer.isPlaying) {
                    mediaPlayer.pause()
                } else {
                    mediaPlayer.play()
                }
            }

        val forward =
            makeButton(
                "+10s"
            ) {
                seekBy(
                    10_000L
                )
            }

        val audio =
            makeButton(
                "ÁUDIO"
            ) {
                showAudioTracks()
            }

        val subtitles =
            makeButton(
                "LEGENDAS"
            ) {
                showSubtitleTracks()
            }

        val openSubtitles =
            makeButton(
                "OPENSubtitles"
            ) {
                showOpenSubtitlesLanguage()
            }

        val subtitleSync =
            makeButton(
                "SYNC LEG."
            ) {
                showSubtitleDelay()
            }

        speedButton =
            makeButton(
                "1.0x"
            ) {
                cycleSpeed()
            }

        aspectButton =
            makeButton(
                "TELA AUTO"
            ) {
                cycleAspectRatio()
            }

        val pip =
            makeButton(
                "PIP"
            ) {
                enterPip()
            }

        listOf(
            back,
            rewind,
            playPause,
            forward,
            audio,
            subtitles,
            openSubtitles,
            subtitleSync,
            speedButton,
            aspectButton,
            pip,
        ).forEach {
            buttonRow.addView(it)
        }

        controlsContainer.addView(
            titleText
        )

        controlsContainer.addView(
            seekBar,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ),
        )

        controlsContainer.addView(
            positionText
        )

        controlsContainer.addView(
            scroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ),
        )

        root.addView(
            controlsContainer,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM,
            ),
        )

        setContentView(root)
    }

    private fun makeButton(
        label: String,
        action: () -> Unit,
    ): Button =
        Button(this).apply {
            text = label

            isAllCaps = false

            setOnClickListener {
                showControls()
                action()
                scheduleControlsHide()
            }
        }

    private fun seekBy(
        delta: Long,
    ) {
        if (!::mediaPlayer.isInitialized) {
            return
        }

        val duration =
            mediaPlayer.length.coerceAtLeast(0L)

        val target =
            (
                mediaPlayer.time +
                    delta
                )
                .coerceAtLeast(0L)
                .let {
                    if (duration > 0L) {
                        it.coerceAtMost(duration)
                    } else {
                        it
                    }
                }

        mediaPlayer.time =
            target
    }

    private fun showAudioTracks() {
        if (!::mediaPlayer.isInitialized) {
            return
        }

        val tracks =
            mediaPlayer.audioTracks

        if (
            tracks == null ||
            tracks.isEmpty()
        ) {
            toast(
                "Nenhuma faixa de áudio disponível."
            )
            return
        }

        val current =
            mediaPlayer.audioTrack

        val checked =
            tracks.indexOfFirst {
                it.id == current
            }

        val labels =
            tracks.map { track ->
                track.name
                    ?: "Áudio ${track.id}"
            }
                .toTypedArray()

        AlertDialog.Builder(this)
            .setTitle(
                "Faixa de áudio"
            )
            .setSingleChoiceItems(
                labels,
                checked,
            ) { dialog, which ->
                mediaPlayer.setAudioTrack(
                    tracks[which].id
                )

                dialog.dismiss()
            }
            .setNegativeButton(
                "Cancelar",
                null,
            )
            .show()
    }

    private fun showSubtitleTracks() {
        if (!::mediaPlayer.isInitialized) {
            return
        }

        val tracks =
            mediaPlayer.spuTracks

        val labels =
            mutableListOf(
                "Desativar legendas"
            )

        tracks
            ?.forEach { track ->
                labels +=
                    (
                        track.name
                            ?: "Legenda ${track.id}"
                        )
            }

        val current =
            mediaPlayer.spuTrack

        var checked = 0

        tracks?.forEachIndexed {
                index,
                track,
            ->
            if (track.id == current) {
                checked =
                    index + 1
            }
        }

        AlertDialog.Builder(this)
            .setTitle(
                "Legendas"
            )
            .setSingleChoiceItems(
                labels.toTypedArray(),
                checked,
            ) { dialog, which ->
                if (which == 0) {
                    mediaPlayer.setSpuTrack(
                        -1
                    )
                } else {
                    val selected =
                        tracks?.getOrNull(
                            which - 1
                        )

                    if (selected != null) {
                        mediaPlayer.setSpuTrack(
                            selected.id
                        )
                    }
                }

                dialog.dismiss()
            }
            .setNeutralButton(
                "Buscar online",
            ) { _, _ ->
                showOpenSubtitlesLanguage()
            }
            .setNegativeButton(
                "Cancelar",
                null,
            )
            .show()
    }

    private fun showOpenSubtitlesLanguage() {
        val languages =
            arrayOf(
                "Português",
                "English",
            )

        AlertDialog.Builder(this)
            .setTitle(
                "Buscar legendas"
            )
            .setItems(
                languages
            ) { _, which ->
                when (which) {
                    0 ->
                        searchOpenSubtitles(
                            "por"
                        )

                    1 ->
                        searchOpenSubtitles(
                            "eng"
                        )
                }
            }
            .setNegativeButton(
                "Cancelar",
                null,
            )
            .show()
    }

    private fun searchOpenSubtitles(
        language: String,
    ) {
        val itemId =
            intent
                .getStringExtra(
                    "item_id"
                )
                ?.toUUIDOrNull()

        if (itemId == null) {
            toast(
                "Não foi possível identificar este item no Jellyfin."
            )
            return
        }

        toast(
            "Buscando legendas..."
        )

        lifecycleScope.launch {
            runCatching {
                subtitleApi
                    .searchRemoteSubtitles(
                        itemId = itemId,
                        language = language,
                        isPerfectMatch = false,
                    )
                    .content
            }
                .onSuccess { results ->
                    val sorted =
                        results
                            .sortedWith(
                                compareByDescending<RemoteSubtitleInfo> {
                                    it.isHashMatch == true
                                }
                                    .thenBy {
                                        it.hearingImpaired == true
                                    }
                                    .thenByDescending {
                                        it.downloadCount
                                            ?: 0
                                    }
                            )
                            .take(
                                30
                            )

                    if (sorted.isEmpty()) {
                        toast(
                            "Nenhuma legenda encontrada."
                        )

                        return@onSuccess
                    }

                    showRemoteSubtitleResults(
                        sorted
                    )
                }
                .onFailure { error ->
                    toast(
                        "Falha ao buscar legendas: ${
                            error.message
                                ?: "erro desconhecido"
                        }"
                    )
                }
        }
    }

    private fun showRemoteSubtitleResults(
        subtitles: List<RemoteSubtitleInfo>,
    ) {
        val labels =
            subtitles
                .map { subtitle ->
                    buildString {
                        append(
                            subtitle.name
                                ?: "Legenda"
                        )

                        subtitle.providerName
                            ?.takeIf {
                                it.isNotBlank()
                            }
                            ?.let {
                                append(
                                    " • $it"
                                )
                            }

                        if (
                            subtitle.isHashMatch ==
                            true
                        ) {
                            append(
                                " • MATCH"
                            )
                        }

                        if (
                            subtitle.hearingImpaired ==
                            true
                        ) {
                            append(
                                " • HI"
                            )
                        }

                        subtitle.downloadCount
                            ?.let {
                                append(
                                    " • $it downloads"
                                )
                            }
                    }
                }
                .toTypedArray()

        AlertDialog.Builder(this)
            .setTitle(
                "OpenSubtitles"
            )
            .setItems(
                labels
            ) { _, which ->
                loadRemoteSubtitle(
                    subtitles[which]
                )
            }
            .setNegativeButton(
                "Cancelar",
                null,
            )
            .show()
    }

    private fun loadRemoteSubtitle(
        subtitle: RemoteSubtitleInfo,
    ) {
        val subtitleId =
            subtitle.id

        if (
            subtitleId.isNullOrBlank()
        ) {
            toast(
                "Legenda sem identificador."
            )
            return
        }

        toast(
            "Baixando legenda..."
        )

        lifecycleScope.launch {
            runCatching {
                val content =
                    subtitleApi
                        .getRemoteSubtitles(
                            subtitleId
                        )
                        .content

                val extension =
                    subtitle.format
                        ?.lowercase(
                            Locale.US
                        )
                        ?.replace(
                            Regex(
                                "[^a-z0-9]"
                            ),
                            "",
                        )
                        ?.takeIf {
                            it.isNotBlank()
                        }
                        ?: "srt"

                val directory =
                    File(
                        cacheDir,
                        "tars_subtitles",
                    ).apply {
                        mkdirs()
                    }

                val file =
                    File(
                        directory,
                        "subtitle_${subtitleId.hashCode()}.$extension",
                    )

                file.writeText(
                    content,
                    Charsets.UTF_8,
                )

                val added =
                    mediaPlayer.addSlave(
                        IMedia.Slave.Type.Subtitle,
                        Uri.fromFile(file),
                        true,
                    )

                if (!added) {
                    error(
                        "LibVLC recusou a legenda"
                    )
                }

                file
            }
                .onSuccess {
                    toast(
                        "Legenda carregada."
                    )

                    showControls()
                }
                .onFailure { error ->
                    toast(
                        "Falha ao carregar legenda: ${
                            error.message
                                ?: "erro desconhecido"
                        }"
                    )
                }
        }
    }

    private fun showSubtitleDelay() {
        if (!::mediaPlayer.isInitialized) {
            return
        }

        val choices =
            arrayOf(
                "-0,5 s",
                "+0,5 s",
                "Zerar atraso",
            )

        AlertDialog.Builder(this)
            .setTitle(
                "Sincronização da legenda"
            )
            .setItems(
                choices
            ) { _, which ->
                val current =
                    mediaPlayer.spuDelay

                val next =
                    when (which) {
                        0 ->
                            current -
                                500_000L

                        1 ->
                            current +
                                500_000L

                        else ->
                            0L
                    }

                mediaPlayer.setSpuDelay(
                    next
                )

                toast(
                    "Atraso da legenda: ${
                        next / 1000
                    } ms"
                )
            }
            .show()
    }

    private fun cycleSpeed() {
        speedIndex =
            (
                speedIndex +
                    1
                ) % speeds.size

        val speed =
            speeds[speedIndex]

        mediaPlayer.rate =
            speed

        speedButton.text =
            String.format(
                Locale.US,
                "%.2gx",
                speed,
            )
    }

    private fun cycleAspectRatio() {
        aspectIndex =
            (
                aspectIndex +
                    1
                ) % aspects.size

        val aspect =
            aspects[aspectIndex]

        mediaPlayer.setAspectRatio(
            aspect
        )

        aspectButton.text =
            if (aspect == null) {
                "TELA AUTO"
            } else {
                "TELA $aspect"
            }
    }

    private fun enterPip() {
        if (
            Build.VERSION.SDK_INT >=
            Build.VERSION_CODES.O
        ) {
            hideControls()

            enterPictureInPictureMode(
                PictureInPictureParams
                    .Builder()
                    .build()
            )
        } else {
            toast(
                "Picture-in-Picture não é suportado neste Android."
            )
        }
    }

    override fun onPictureInPictureModeChanged(
        isInPictureInPictureMode: Boolean,
        newConfig: android.content.res.Configuration,
    ) {
        super.onPictureInPictureModeChanged(
            isInPictureInPictureMode,
            newConfig,
        )

        if (
            isInPictureInPictureMode
        ) {
            hideControls()
        } else {
            showControls()
        }
    }

    private fun showControls() {
        if (!::controlsContainer.isInitialized) {
            return
        }

        controlsContainer.visibility =
            View.VISIBLE

        controlsVisible = true

        scheduleControlsHide()
    }

    private fun hideControls() {
        if (!::controlsContainer.isInitialized) {
            return
        }

        controlsContainer.removeCallbacks(
            hideControlsRunnable
        )

        controlsContainer.visibility =
            View.GONE

        controlsVisible = false

        hideSystemUi()
    }

    private fun scheduleControlsHide() {
        if (!::controlsContainer.isInitialized) {
            return
        }

        controlsContainer.removeCallbacks(
            hideControlsRunnable
        )

        if (
            ::mediaPlayer.isInitialized &&
            mediaPlayer.isPlaying
        ) {
            controlsContainer.postDelayed(
                hideControlsRunnable,
                4_000L,
            )
        }
    }

    @Suppress("DEPRECATION")
    private fun hideSystemUi() {
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_FULLSCREEN or
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
    }

    @Deprecated(
        "Deprecated in Java"
    )
    override fun onBackPressed() {
        finishWithResult(false)
    }

    private fun finishWithResult(
        ended: Boolean,
    ) {
        if (returnedResult) {
            return
        }

        returnedResult = true

        val position =
            if (::mediaPlayer.isInitialized) {
                mediaPlayer.time
                    .coerceAtLeast(0L)
            } else {
                0L
            }

        val duration =
            if (::mediaPlayer.isInitialized) {
                mediaPlayer.length
                    .coerceAtLeast(0L)
            } else {
                0L
            }

        val finalPosition =
            if (
                ended &&
                duration > 0L
            ) {
                duration
            } else {
                position
            }

        setResult(
            Activity.RESULT_OK,
            Intent(
                Constants.VLC_PLAYER_RESULT_ACTION
            ).apply {
                putExtra(
                    "extra_position",
                    finalPosition,
                )

                putExtra(
                    "extra_duration",
                    duration,
                )
            },
        )

        finish()
    }

    override fun onDestroy() {
        if (::controlsContainer.isInitialized) {
            controlsContainer.removeCallbacks(
                hideControlsRunnable
            )
        }

        if (::seekBar.isInitialized) {
            seekBar.removeCallbacks(
                progressUpdater
            )
        }

        if (::mediaPlayer.isInitialized) {
            mediaPlayer.stop()
            mediaPlayer.detachViews()
            mediaPlayer.release()
        }

        if (::libVLC.isInitialized) {
            libVLC.release()
        }

        super.onDestroy()
    }

    private fun formatTime(
        ms: Long,
    ): String {
        val totalSeconds =
            ms.coerceAtLeast(0L) /
                1000L

        val hours =
            totalSeconds /
                3600L

        val minutes =
            (
                totalSeconds %
                    3600L
                ) / 60L

        val seconds =
            totalSeconds %
                60L

        return if (
            hours > 0L
        ) {
            "%d:%02d:%02d".format(
                hours,
                minutes,
                seconds,
            )
        } else {
            "%02d:%02d".format(
                minutes,
                seconds,
            )
        }
    }

    private fun toast(
        message: String,
    ) {
        Toast.makeText(
            this,
            message,
            Toast.LENGTH_SHORT,
        ).show()
    }
}
