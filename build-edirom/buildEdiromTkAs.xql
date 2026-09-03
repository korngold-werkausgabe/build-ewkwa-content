xquery version "3.1";

declare namespace edirom = "http://www.edirom.de/ns/1.3";
declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace transform = "http://exist-db.org/xquery/transform";
declare namespace xmldb = "http://exist-db.org/xquery/xmldb";
declare namespace array = "http://www.w3.org/2005/xpath-functions/array";
declare namespace util = "http://exist-db.org/xquery/util";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";
declare namespace math = "http://www.w3.org/2005/xpath-functions/math";

declare variable $cnList as xs:string? external := "";
declare variable $cnListFile as xs:string? external := "";
declare variable $collectionPath as xs:string external;
declare variable $sourcesPath as xs:string external;
declare variable $subDiv as xs:string external;
declare variable $volumeName as xs:string external;

(: --- Hilfsfunktion für Pfadbau --- :)
declare function local:composePath($volume as xs:string, $subDiv as xs:string?, $rest as xs:string) as xs:string {
  if ($subDiv and $subDiv != "" and $subDiv != "None")
  then "xmldb:exist:///db/apps/edirom-content/" || $volume || "/" || $subDiv || "/" || $rest
  else "xmldb:exist:///db/apps/edirom-content/" || $volume || "/" || $rest
};

declare function local:normalize-text-nodes($node as node()) as node() {
  typeswitch($node)
    case text()
      return
        if (normalize-space($node) = '') then
          $node
        else
          text { normalize-space($node) }
    case element() return element { node-name($node) } {
      $node/@*,
      for $child in $node/node()
      return local:normalize-text-nodes($child)
    }
    default return $node
};

declare function local:textRendition($node as node()?) as xs:string {
  $node/normalize-space()
};

declare function local:buildSiglum($node as node()?, $sources as node()*, $subDiv as xs:string, $volumeName as xs:string) as xs:string {
  $node/@siglum/normalize-space()
};

declare function local:buildMeasures($measures as node()?) as xs:string {
  let $measures-string := for $node in $measures/*
  return
    switch ($node/name())
      case 'measure'
        return
          $node/@label/string()
      case 'sequence'
        return
          concat($node/@label-from/string(), '–', $node/@label-to/string())
      default
        return
          ''
  return
    concat('T. ', string-join($measures-string, ', '))
};

declare function local:buildPitch($pitch as node()*) as xs:string {
  let $pname := if (xs:int($pitch/@oct/normalize-space()) <= 2)
  then
    upper-case($pitch/@pname/normalize-space())
  else
    $pitch/@pname/normalize-space()
  let $oct := if (xs:int($pitch/@oct/normalize-space()) >= 4)
  then
    xs:int($pitch/@oct/normalize-space()) - 3
  else
    if (xs:int($pitch/@oct/normalize-space()) >= 2)
    then
      ()
    else
      if (xs:int($pitch/@oct/normalize-space()) = 1)
      then
        1
      else
        0
  return
    concat($pname, if ($oct) then concat('', $oct) else '')
};

declare function local:buildChord($chord as node()*) as xs:string {
  string-join(
    for $pitch in $chord/pitch
    return
      local:buildPitch($pitch),
    '/'
  )
};

declare function local:buildSequence($sequence as node()*) as xs:string {
  string-join(
    for $pitch in $sequence/pitch
    return
      local:buildPitch($pitch),
    '–'
  )
};

declare function local:buildSmufl($symbol as xs:string) as xs:string {
  ''
};

declare function local:buildNoteTextContent($nodes as node()*, $sources as node()*, $subDiv as xs:string, $volumeName as xs:string, $pos as xs:integer) as xs:string {
  let $result :=
    for $node at $index in $nodes[position() >= $pos]
    return
      if ($node/self::element()) then
        switch ($node/name())
          case 'measures'
            return local:buildMeasures($node)
          case 'siglum'
            return local:buildSiglum($node, $sources, $subDiv, $volumeName)
          case 'pitch'
            return local:buildPitch($node)
          case 'chord'
            return local:buildChord($node)
          case 'pitch-sequence'
            return local:buildSequence($node)
          case 'musicalSymbol'
            return local:buildSmufl($node/@url/string())
          case 'rend'
            return local:textRendition($node)
          default
            return ''
      else
        let $nextNode := $nodes[$pos + $index]
        let $isNextElement := $nextNode/name() != ''
        return
          if ($isNextElement and $node/string() != '' and not(ends-with($node/string(), ' ')) and not(ends-with($node/string(), '('))) then
            concat($node/string(), ' ')
          else
            $node/string()
  return
    string-join($result, '')
};

declare function local:convertToMeasuresElement($measure-string as xs:string*, $siglum as xs:string*, $mdiv as xs:string*) as node()* {
  if (contains($measure-string, ',')) then
    (
    let $measure-substrings := tokenize($measure-string, ', ')
    let $tmp-measures := <measures>
      {
        for $item in $measure-substrings
        return
          <measure
            siglum="{$siglum}"
            mdiv="{$mdiv}"
            label="{$item}"/>
      }</measures>
    return
      $tmp-measures
    )
  else
    (
    if (contains($measure-string, '–')) then
      (
      let $measures := tokenize($measure-string, '–')
      let $tmp-sequence := <measures><sequence
          siglum="{$siglum}"
          label-from="{$measures[1]}"
          label-to="{$measures[2]}"
          mdiv="{$mdiv}"/></measures>
      return
        $tmp-sequence
      )
    else
      (
      <measures><measure
          siglum="{$siglum}"
          mdiv="{$mdiv}"
          label="{$measure-string}"/></measures>
      )
    )
};

declare function local:populatePlist($sources as node()*, $measures as node(), $subDiv as xs:string*) as xs:string {
  string-join(
    for $sub-node in $measures/*
    return
      switch ($sub-node/name())
        case 'measure'
          return
            local:measureUri($sources, $sub-node, $subDiv)
        case 'sequence'
          return
            string-join(for $m in (xs:integer($sub-node/@label-from/string()) to xs:integer($sub-node/@label-to/string()))
            return
              local:measureUri($sources, <measure
                siglum="{$sub-node/@siglum/string()}"
                mdiv="{$sub-node/@mdiv/string()}"
                label="{$m}"/>, $subDiv), ' ')
        default
          return
            '',
    ' '
  )
};

declare function local:measureUri($sources as node()*, $measure as node()*, $subDiv as xs:string*) as xs:string {
  try {
    let $url := local:composePath($volumeName, $subDiv, "sources/")
    let $sourceDoc := ($sources//mei:mei[.//mei:identifier[text() = string($measure/@siglum)]][1], ())[1]
    return
      if (not($sourceDoc)) then
        xs:string('')
      else
        let $base := xs:string(replace(base-uri($sourceDoc), '^(.*/)(.*?\.\w+)$', '$2'))
        let $mdiv-name := xs:string($measure/@mdiv)
        let $label-name := xs:string($measure/@label)
        let $found-measure := ($sourceDoc//mei:mdiv[@n = $mdiv-name]//mei:measure[@n = $label-name], ())[1]
        let $measure-id := if ($found-measure) then xs:string($found-measure/@xml:id) else xs:string('')
        return
          if ($measure-id = '') then
            xs:string('')
          else
            xs:string(concat($url, $base, '#', $measure-id))
  } catch * {
    xs:string('')
  }
};

declare function local:generate-uuid() as xs:string {
  let $rng := fn:random-number-generator()
  let $hex-chars := ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f')
  let $random-hex := function ($length as xs:integer) {
    string-join(for $i in 1 to $length
    return
      $hex-chars[xs:integer($rng('next')()('number') * 16) + 1], '')
  }
  let $pad := function ($str as xs:string, $length as xs:integer) {
    let $padding := string-join(for $i in 1 to ($length - string-length($str))
    return
      '0', '')
    return
      concat($padding, $str)
  }
  return
    concat(
    $pad($random-hex(8), 8), '-',
    $pad($random-hex(4), 4), '-',
    '4', $pad($random-hex(3), 3), '-',
    ('8', '9', 'a', 'b')[xs:integer($rng('next')()('number') * 4) + 1],
    $pad($random-hex(3), 3), '-',
    $pad($random-hex(12), 12)
    )
};

(: Paths and input documents :)

let $cnListNode :=
  if ($cnListFile != "") then
    doc($cnListFile)
  else
    parse-xml-fragment($cnList)
let $sources := collection($sourcesPath)

let $plist := map:merge(for $note in $cnListNode//criticalNote
return
  map:entry($note/@xml:id/string(), string-join(for $measure in $note/noteText//measure
  return
    local:measureUri($sources, $measure, $subDiv), ' '))
)

let $criticalNotes :=
    <cnList> {
        for $note in $cnListNode//*:criticalNote
          let $mainSourcePlist := local:populatePlist($sources, local:convertToMeasuresElement(fn:string($note/*:measures/text()), $cnListNode/*:kb/@mainSource/string(), $cnListNode/*:kb/@n/string()), $subDiv)
          let $titleText :=
            string-join(
              (
                if ($note/*:measures[normalize-space()]) then concat('T. ', $note/*:measures/normalize-space()) else (),
                if ($note/*:staff[normalize-space()]) then $note/*:staff/normalize-space() else (),
                if ($note/*:musicalEvent[normalize-space()]) then $note/*:musicalEvent/normalize-space() else ()
              )[. != ''],
              ' | '
            )
          return
            <annot
              xmlns="http://www.music-encoding.org/ns/mei"
              xml:id="{$note/@xml:id}"
              type="editorialComment"
              class="#ediromAnnotPrio1 {concat('#', string-join($note/*:categories/@values/data(), ' '))}"
              plist="{string-join(for $item in ($mainSourcePlist, map:get($plist, $note/@xml:id/string())) return if ($item) then string($item) else (), ' ')}"
            >
              <title
                xml:lang="de">{$titleText}</title>
              <p>{
                  local:buildNoteTextContent($note/*:noteText/node(), $sources, $subDiv, $volumeName, 1)
              }</p>
          </annot>}
    </cnList>

return
  $criticalNotes