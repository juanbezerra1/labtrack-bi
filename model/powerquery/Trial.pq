// labtrack-bi: query of the table Trial (fact_trial.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Trial.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\fact_trial.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Dropped = Table.RemoveColumns(Headers, {"session_key", "date_key", "modality"}),
    Cleaned = Table.ReplaceValue(Dropped, "", null, Replacer.ReplaceValue, {"trial_key", "recording_key", "condition", "trial_no", "onset_s", "duration_s", "valid", "reject_reason", "rms_mean_uv", "mnf_hz", "mdf_hz", "alpha_power_uv2", "peak_force_n", "force_cv_pct"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"trial_key", Int64.Type}, {"recording_key", Int64.Type}, {"condition", type text}, {"trial_no", Int64.Type}, {"onset_s", type number}, {"duration_s", type number}, {"valid", type logical}, {"reject_reason", type text}, {"rms_mean_uv", type number}, {"mnf_hz", type number}, {"mdf_hz", type number}, {"alpha_power_uv2", type number}, {"peak_force_n", type number}, {"force_cv_pct", type number}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"reject_reason", each if _ = null then null else Text.Proper(Text.Replace(_, "_", " ")), type text}}),
    AddValidity = Table.AddColumn(Labelled, "Validity", each if [valid] then "Valid" else "Rejected", type text),
    AddFeedback = Table.AddColumn(AddValidity, "Feedback", each if Text.EndsWith([condition], "_nofb") then "Off" else if Text.EndsWith([condition], "_fb") then "On" else null, type text),
    AddHoldLevel = Table.AddColumn(AddFeedback, "Hold Level", each if Text.StartsWith([condition], "hold_") then Int64.From(Number.FromText(Text.Middle([condition], 5, 2))) else null, Int64.Type),
    AddFatiguePhase = Table.AddColumn(AddHoldLevel, "Fatigue Phase", each if Text.StartsWith([condition], "fatigue_") then (if Text.EndsWith([condition], "_post") then "Post" else "Pre") else null, type text),
    AddStimulusSize = Table.AddColumn(AddFatiguePhase, "Stimulus Size", each if Text.StartsWith([condition], "stimulus_") then (if Text.EndsWith([condition], "_large") then "Large" else "Small") else null, type text),
    Renamed = Table.RenameColumns(AddStimulusSize, {{"trial_key", "Trial Key"}, {"recording_key", "Recording Key"}, {"condition", "Condition"}, {"trial_no", "Trial No"}, {"onset_s", "Onset Seconds"}, {"duration_s", "Duration Seconds"}, {"valid", "Valid"}, {"reject_reason", "Reject Reason"}, {"rms_mean_uv", "RMS"}, {"mnf_hz", "MNF"}, {"mdf_hz", "MDF"}, {"alpha_power_uv2", "Alpha Power"}, {"peak_force_n", "Peak Force"}, {"force_cv_pct", "Force CV"}}),
    Selected = Table.SelectColumns(Renamed, {"Trial Key", "Recording Key", "Condition", "Trial No", "Onset Seconds", "Duration Seconds", "Valid", "Validity", "Reject Reason", "Feedback", "Hold Level", "Fatigue Phase", "Stimulus Size", "RMS", "MNF", "MDF", "Alpha Power", "Peak Force", "Force CV"})
in
    Selected
