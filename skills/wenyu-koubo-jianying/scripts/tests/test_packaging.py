"""v2 synthetic invariant tests; no real media, native app, network or registration."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_packaging import (MANAGED_KEY, LEGACY_KEY, PackagingError, build_packaging,
                             load_json, main, validate_packaging, write_staged)


def fixtures():
    clips = []
    for sid, start, target, text in (("a", 5000000, 0, "先讲结论再给原因"),
                                    ("b", 1000000, 2000000, "完整例子支撑观点"),
                                    ("a", 1000000, 4000000, "最后保留成立条件")):
        clips.append({"source_id": sid, "source_start_us": start, "source_end_us": start+2000000,
                      "target_start_us": target, "speed": 1, "speaker_status": "confirmed_target",
                      "word_intervals": [{"start_us": start+100000, "end_us": start+1900000, "text": text}]})
    rough = {"sources": [{"id":"a","duration_us":9000000},{"id":"b","duration_us":9000000}],
             "clips":clips,"canvas":{"width":1080,"height":1920},"approved":True,
             "approval_reference":"Synthetic claim only","speaker_identity_confirmed":True}
    event = {"id":"e1","role":"emphasis","clip_index":1,"source_start_us":1200000,"source_end_us":2500000,
             "text":"完整例子，支撑观点","evidence_quote":"完整例子支撑观点","reason":"突出论据作用",
             "style":{"size":18},"highlights":[{"word":"支撑","color":[1,0.3,0.2]}],"motion":"pop"}
    packaging = {"texts":[event]}
    caption = {"id":"native-caption","type":"subtitle","content":json.dumps({"text":"剪映原生识别字幕",
               "styles":[{"range":[0,8],"font":{"id":"known-native-font","path":"/native/cache/font.ttf"}}]}),
               "native_recognition_metadata":{"task_id":"synthetic-native-claim"}}
    draft = {"id":"synthetic-native","duration":6000000,"fps":30,"canvas_config":{"width":1080,"height":1920,"ratio":"original"},
             "platform":{"os":"mac","app_version":"11.6.0"},"last_modified_platform":{"os":"mac"},
             "config":{"subtitle_keywords_config":{"native":"preserve"}},"unknown":{"future":[1,2]},
             "tracks":[{"id":"video-track","type":"video","name":"原片","segments":[{"id":"v1","material_id":"m1",
               "render_index":0,"target_timerange":{"start":0,"duration":6000000},"source_timerange":{"start":1,"duration":6000000},
               "clip":{"rotation":0},"hdr_settings":{"nits":4000},"volume":0.8}]},
               {"id":"native-caption-track","type":"text","name":"原生识别字幕","segments":[{"id":"c1","material_id":"native-caption",
                "render_index":17000,"target_timerange":{"start":0,"duration":6000000},"visible":True}]}],
             "materials":{"videos":[{"id":"m1","path":"/fake/original.MOV"}],"texts":[caption],
                          "text_templates":[{"id":"native-existing-template"}],"effects":[{"id":"original-effect"}]}}
    return rough, packaging, draft


def chapter():
    return {"id":"chapter1","role":"chapter","source_spans":[
        {"clip_index":0,"source_start_us":5000000,"source_end_us":7000000},
        {"clip_index":1,"source_start_us":1000000,"source_end_us":3000000},
        {"clip_index":2,"source_start_us":1000000,"source_end_us":3000000}],
        "style":{"size":18},"text":"先给结论，再用例子说明","verbatim":False,"evidence_quote":"先讲结论再给原因", "reason":"持续提示当前章节","motion":"pop"}


class PackagingV2Tests(unittest.TestCase):
    def test_missing_size_does_not_silently_generate_small_text(self):
        rough, plan, draft = fixtures()
        del plan["texts"][0]["style"]
        with self.assertRaisesRegex(PackagingError, "style.size is required"):
            build_packaging(rough, plan, draft)

    def test_unresolved_tail_risk_blocks_packaging_and_cli_validation(self):
        rough, plan, draft = fixtures()
        rough["clips"][0]["word_intervals"][-1]["end_us"] = 6990000
        report = validate_packaging(rough, plan)
        self.assertFalse(report["ready_for_staging"])
        self.assertEqual(report["continuity_risks"][0]["clip_index"], 0)
        with self.assertRaisesRegex(PackagingError, "not ready"):
            build_packaging(rough, plan, draft)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "rough.json").write_text(json.dumps(rough))
            (d / "package.json").write_text(json.dumps(plan))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--rough-plan", str(d / "rough.json"),
                                       "--packaging-plan", str(d / "package.json"),
                                       "--validate-only"]), 2)

    def test_no_plain_text_pseudo_subtitles(self):
        rough, plan, _ = fixtures(); plan["captions"]=[{"text":"普通文字伪字幕"}]
        with self.assertRaisesRegex(PackagingError,"recognize subtitles in Jianying"):
            validate_packaging(rough,plan)

    def test_preserves_all_existing_recognition_tracks_materials_platform_and_hdr(self):
        rough,plan,draft=fixtures(); before=copy.deepcopy((rough,plan,draft))
        staged,report=build_packaging(rough,plan,draft)
        self.assertEqual((rough,plan,draft),before)
        self.assertEqual(staged["tracks"][:2],draft["tracks"])
        self.assertEqual(staged["materials"]["texts"][:1],draft["materials"]["texts"])
        for key in draft:
            if key not in ("tracks","materials"):self.assertEqual(staged[key],draft[key])
        for key in draft["materials"]:
            if key!="texts":self.assertEqual(staged["materials"][key],draft["materials"][key])
        self.assertFalse(report["ordinary_subtitles_generated"])
        self.assertFalse(report["native_subtitle_origin_verified"])
        self.assertEqual(report["preserved_existing_text_tracks"],1)

    def test_reordered_sources_map_by_clip_index(self):
        rough,plan,_=fixtures();row=validate_packaging(rough,plan)["mapped"]["texts"][0]
        self.assertEqual((row["target_start_us"],row["duration_us"]),(2200000,1300000))
        self.assertEqual(row["source_spans"][0]["source_id"],"b")

    def test_one_persistent_chapter_over_multiple_cuts_and_sources_with_only_one_pop(self):
        rough,plan,draft=fixtures();plan["texts"]=[chapter()]
        staged,report=build_packaging(rough,plan,draft)
        segments=staged["tracks"][-1]["segments"]
        self.assertEqual(len(segments),1)
        self.assertEqual(segments[0]["target_timerange"],{"start":0,"duration":6000000})
        keys=segments[0]["common_keyframes"][0]["keyframe_list"]
        self.assertEqual([k["time_offset"] for k in keys],[0,80000,160000])
        self.assertEqual(len(report["mapped"]["texts"][0]["source_spans"]),3)

    def test_persistent_spans_cannot_skip_cut_or_cross_deleted_time(self):
        for mode in ("skip","source_outside","target_gap"):
            rough,plan,_=fixtures();ch=chapter()
            if mode=="skip":ch["source_spans"].pop(1)
            elif mode=="source_outside":ch["source_spans"][0]["source_start_us"]=4900000
            else:ch["source_spans"][0]["source_end_us"]=6900000
            plan["texts"]=[ch]
            with self.subTest(mode=mode),self.assertRaises(PackagingError):validate_packaging(rough,plan)

    def test_roles_and_layers_allow_simultaneous_explanation_and_emphasis(self):
        rough,plan,draft=fixtures();ex=copy.deepcopy(plan["texts"][0]);ex.update(id="ex",role="explanation",layer=3)
        plan["texts"].append(ex);plan["texts"].append(chapter())
        staged,_=build_packaging(rough,plan,draft)
        self.assertEqual(len(staged["tracks"])-len(draft["tracks"]),3)
        indices=[t["segments"][0]["render_index"] for t in staged["tracks"][-3:]]
        self.assertEqual(indices,[17001,17002,17003])
        self.assertIn("chapter",staged["tracks"][-3]["name"])

    def test_same_role_layer_overlap_refused_but_distinct_layer_allowed(self):
        rough,plan,draft=fixtures();e=copy.deepcopy(plan["texts"][0]);e["id"]="e2";plan["texts"].append(e)
        with self.assertRaisesRegex(PackagingError,"same role/layer"):validate_packaging(rough,plan)
        e["layer"]=51
        self.assertEqual(build_packaging(rough,plan,draft)[1]["new_packaging_tracks"],2)

    def test_adjacent_chapters_half_open_ranges_do_not_overlap(self):
        rough,plan,_=fixtures();a=chapter();a["source_spans"]=a["source_spans"][:1]
        b=chapter();b["id"]="chapter2";b["source_spans"]=b["source_spans"][1:];b["evidence_quote"]="完整例子支撑观点"
        plan["texts"]=[a,b];result=validate_packaging(rough,plan)["mapped"]["texts"]
        self.assertEqual(result[0]["target_start_us"]+result[0]["duration_us"],result[1]["target_start_us"])

    def test_no_outline_shadow_copied_to_all_highlight_runs(self):
        rough,plan,draft=fixtures();plan["texts"][0]["style"]={"size":7,"border":None,"shadow":{"alpha":0.65,"diffuse":18,"distance":4,"angle":-30}}
        staged,_=build_packaging(rough,plan,draft);material=staged["materials"]["texts"][-1]
        self.assertEqual(material["check_flag"],39)
        runs=json.loads(material["content"])["styles"]
        self.assertEqual([r["range"] for r in runs],[[0,5],[5,7],[7,9]])
        for run in runs:
            self.assertEqual(run["strokes"],[])
            self.assertEqual(run["shadows"][0]["alpha"],0.65)
            self.assertAlmostEqual(run["shadows"][0]["diffuse"],18/600)
            self.assertEqual(run["size"],7)

    def test_font_copies_only_current_native_metadata_to_each_run(self):
        rough,plan,draft=fixtures();plan["texts"][0]["style"]={"size":18,"font":{"from_material_id":"native-caption"}}
        staged,_=build_packaging(rough,plan,draft)
        for run in json.loads(staged["materials"]["texts"][-1]["content"])["styles"]:
            self.assertEqual(run["font"],{"id":"known-native-font","path":"/native/cache/font.ttf"})
        self.assertEqual(staged["materials"]["texts"][0],draft["materials"]["texts"][0])

    def test_placeholder_or_invented_font_is_refused(self):
        rough,plan,draft=fixtures();plan["texts"][0]["style"]={"size":18,"font":"凭空字体名"}
        with self.assertRaisesRegex(PackagingError,"font supports"):validate_packaging(rough,plan)
        plan["texts"][0]["style"]={"size":18,"font":{"from_material_id":"native-caption"}}
        content=json.loads(draft["materials"]["texts"][0]["content"]);content["styles"][0]["font"]["path"]="D:"
        draft["materials"]["texts"][0]["content"]=json.dumps(content)
        with self.assertRaisesRegex(PackagingError,"placeholder"):build_packaging(rough,plan,draft)

    def test_ui_font_size_not_falsely_mapped_to_json(self):
        rough,plan,_=fixtures();plan["texts"][0]["style"]={"ui_font_size":13}
        with self.assertRaisesRegex(PackagingError,"unsupported fields"):validate_packaging(rough,plan)

    def test_native_linear_position_keyframes_serialize_within_one_chapter(self):
        rough,plan,draft=fixtures();ch=chapter();ch["keyframes"]=[{"property":"y","points":[{"time_offset_us":0,"value":0.5},{"time_offset_us":3000000,"value":0.6}]}]
        plan["texts"]=[ch];staged,_=build_packaging(rough,plan,draft);keys=staged["tracks"][-1]["segments"][0]["common_keyframes"]
        self.assertEqual([k["property_type"] for k in keys],["KFTypeScaleX","KFTypePositionY"])
        self.assertEqual(keys[1]["keyframe_list"][1]["time_offset"],3000000)
        self.assertEqual(staged["tracks"][-1]["segments"][0]["extra_material_refs"],[])

    def test_outside_or_duplicate_keyframes_and_pop_scale_conflict_refused(self):
        for prop,points in (("scale",[{"time_offset_us":0,"value":1},{"time_offset_us":1,"value":1}]),
                            ("alpha",[{"time_offset_us":0,"value":1},{"time_offset_us":1,"value":1}]),
                            ("x",[{"time_offset_us":0,"value":0},{"time_offset_us":1300000,"value":0}])):
            rough,plan,_=fixtures();plan["texts"][0]["keyframes"]=[{"property":prop,"points":points}]
            with self.subTest(prop=prop),self.assertRaises(PackagingError):validate_packaging(rough,plan)

    def test_checkpoint_refuses_second_half_and_reports_stop_without_touching_video(self):
        rough,plan,draft=fixtures();plan["checkpoint_end_us"]=3500000
        staged,report=build_packaging(rough,plan,draft)
        self.assertTrue(report["stop_at_checkpoint"]);self.assertEqual(report["remaining_packaging_status"],"not_started")
        self.assertEqual(staged["duration"],6000000)
        self.assertEqual(staged["tracks"][:2],draft["tracks"])
        plan["checkpoint_end_us"]=3000000
        with self.assertRaisesRegex(PackagingError,"checkpoint"):validate_packaging(rough,plan)

    def test_no_image_or_sound_effect_capability_is_faked(self):
        for key in ("images","sfx","audio"):
            rough,plan,_=fixtures();plan[key]=[{"path":"fake"}]
            with self.subTest(key=key),self.assertRaisesRegex(PackagingError,"unsupported"):validate_packaging(rough,plan)

    def test_evidence_verbatim_and_semantic_status(self):
        rough,plan,_=fixtures();plan["texts"][0]["text"]="论据 → 观点";plan["texts"][0]["highlights"]=[]
        with self.assertRaisesRegex(PackagingError,"verbatim"):validate_packaging(rough,plan)
        plan["texts"][0]["verbatim"]=False;report=validate_packaging(rough,plan)
        self.assertFalse(report["semantic_review_verified"])
        plan["texts"][0]["evidence_quote"]="另一段并未说的话"
        with self.assertRaisesRegex(PackagingError,"evidence_quote"):validate_packaging(rough,plan)

    def test_speed_rejected_instead_of_retiming_original(self):
        for update in ({"speed":1.2},{"speed":True},{"speed_curve":[1,2]},{"reverse":True}):
            rough,plan,_=fixtures();rough["clips"][0].update(update)
            with self.subTest(update=update),self.assertRaises(PackagingError):validate_packaging(rough,plan)

    def test_duplicate_ids_or_managed_application_refused(self):
        rough,plan,draft=fixtures();staged,_=build_packaging(rough,plan,draft)
        with self.assertRaisesRegex(PackagingError,"already present"):build_packaging(rough,plan,staged)
        draft[LEGACY_KEY]={"schema_version":1}
        with self.assertRaisesRegex(PackagingError,"migration"):build_packaging(rough,plan,draft)
        e=copy.deepcopy(plan["texts"][0]);plan["texts"].append(e)
        with self.assertRaisesRegex(PackagingError,"unique"):validate_packaging(rough,plan)

    def test_plaintext_and_exclusive_output_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"stage.json"
            for value in ('encrypted','"encoded"','{"id":1,"id":2}','{"x":NaN}'):
                p.write_text(value)
                with self.subTest(value=value),self.assertRaises(PackagingError):load_json(p)
            p.write_text("original")
            with self.assertRaises(PackagingError):write_staged(p,{"x":1})
            self.assertEqual(p.read_text(),"original")
            with self.assertRaises(PackagingError):write_staged(p,{},p)
            with self.assertRaises(PackagingError):write_staged(Path(tmp)/"draft_info.json",{})
            native=Path(tmp)/"com.lveditor.draft";native.mkdir();alias=Path(tmp)/"alias";alias.symlink_to(native,target_is_directory=True)
            with self.assertRaises(PackagingError):write_staged(alias/"new.json",{})

    def test_deterministic_cli_new_file_and_validate_only(self):
        rough,plan,draft=fixtures();self.assertEqual(build_packaging(rough,plan,draft)[0],build_packaging(rough,plan,draft)[0])
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for name,value in (("rough",rough),("plan",plan),("draft",draft)):(d/(name+".json")).write_text(json.dumps(value))
            argv=["--rough-plan",str(d/"rough.json"),"--packaging-plan",str(d/"plan.json")]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(argv+["--validate-only"]),0)
                self.assertEqual(len(list(d.iterdir())),3)
                full=argv+["--draft-input",str(d/"draft.json"),"--out",str(d/"new.json")]
                self.assertEqual(main(full),0);self.assertEqual(main(full),2)
            self.assertEqual(json.loads((d/"draft.json").read_text()),draft)

    def test_layer_and_native_compatibility_fields(self):
        rough,plan,draft=fixtures();draft["tracks"][0]["render_index"]=22000
        staged,_=build_packaging(rough,plan,draft);segment=staged["tracks"][-1]["segments"][0]
        self.assertEqual(segment["render_index"],22001);self.assertIs(segment["is_tone_modify"],False)
        self.assertNotIn("hdr_settings",segment);self.assertEqual(staged["platform"],draft["platform"])

    def test_approval_and_duration_canvas_still_checked(self):
        for field in ("approval","duration","canvas"):
            rough,plan,draft=fixtures()
            if field=="approval":rough["approved"]=False
            elif field=="duration":draft["duration"]+=1
            else:draft["canvas_config"]["width"]=1920
            with self.subTest(field=field),self.assertRaises(PackagingError):build_packaging(rough,plan,draft)

    def test_legacy_emphasis_only_without_caption_still_works(self):
        rough,plan,draft=fixtures();plan={"emphasis":plan["texts"]}
        staged,report=build_packaging(rough,plan,draft)
        self.assertEqual(report["new_packaging_tracks"],1)
        self.assertFalse(staged[MANAGED_KEY]["ordinary_subtitles_generated"])

if __name__=="__main__":unittest.main()
