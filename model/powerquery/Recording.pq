// labtrack-bi: query of the table Recording (fact_recording.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Recording.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\fact_recording.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Dropped = Table.RemoveColumns(Headers, {"date_key", "n_trials", "n_valid_trials"}),
    Cleaned = Table.ReplaceValue(Dropped, "", null, Replacer.ReplaceValue, {"recording_key", "session_key", "device_key", "modality", "sampling_rate_hz", "n_channels", "duration_s", "size_mb", "qc", "device_calibrated"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"recording_key", Int64.Type}, {"session_key", Int64.Type}, {"device_key", Int64.Type}, {"modality", type text}, {"sampling_rate_hz", Int64.Type}, {"n_channels", Int64.Type}, {"duration_s", type number}, {"size_mb", type number}, {"qc", type text}, {"device_calibrated", type logical}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"modality", each if _ = null then null else Record.FieldOrDefault([emg = "EMG", eeg = "EEG", force = "Force"], _, _), type text}, {"qc", each if _ = null then null else Text.Proper(Text.Replace(_, "_", " ")), type text}}),
    AddCalibration = Table.AddColumn(Labelled, "Calibration", each if [device_calibrated] then "Calibrated" else "Not calibrated", type text),
    Renamed = Table.RenameColumns(AddCalibration, {{"recording_key", "Recording Key"}, {"session_key", "Session Key"}, {"device_key", "Device Key"}, {"modality", "Modality"}, {"sampling_rate_hz", "Sampling Rate Hz"}, {"n_channels", "Channels"}, {"duration_s", "Duration Seconds"}, {"size_mb", "Size MB"}, {"qc", "QC"}, {"device_calibrated", "Device Calibrated"}}),
    Selected = Table.SelectColumns(Renamed, {"Recording Key", "Session Key", "Device Key", "Modality", "Sampling Rate Hz", "Channels", "Duration Seconds", "Size MB", "QC", "Device Calibrated", "Calibration"})
in
    Selected
