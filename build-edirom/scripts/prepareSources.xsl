<?xml version="1.0" encoding="UTF-8"?>
<!--
  Stylesheet: prepareSources.xsl
  Purpose:
    Prepare a MEI source document for inclusion in the edition by rewriting the
    file description and replacing the original manifestation metadata with a
    project-specific source description. This keeps the source record aligned
    with the edition package while preserving the original musical content.

  Inputs:
    - A source MEI file with a fileDesc section.
    - Parameters: $title, $sigle, $manifestationFile

  Output:
    - A normalized MEI file that carries the edition title, the siglum, and the
      manifestation metadata from the supplied source description.
-->
<xsl:stylesheet xmlns:mei="http://www.music-encoding.org/ns/mei"
  xmlns="http://www.music-encoding.org/ns/mei"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <xsl:output indent="yes"/>
  <!-- Title assigned to the prepared source file in the edition context. -->
  <xsl:param name="title" select="''"/>
  <!-- Siglum used as the edition-specific identifier for the source. -->
  <xsl:param name="sigle" select="''"/>
  <!-- External manifestation document whose manifestation nodes are copied in. -->
  <xsl:param name="manifestationFile" select="''"/>

  <!-- Default identity copy rule for all nodes not specifically rewritten. -->
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Replace the file description with a project-specific metadata block that
       contains the edition title, the siglum, and the manifestation list. -->
  <xsl:template match="mei:fileDesc">
    <mei:fileDesc>
      <mei:titleStmt>
        <mei:title><xsl:value-of select="$title"/></mei:title>
      </mei:titleStmt>
      <editionStmt>
        <edition>
          <identifier type="siglum"><xsl:value-of select="$sigle"/></identifier>
        </edition>
        </editionStmt>
      <mei:manifestationList>
        <xsl:copy-of select="document($manifestationFile)/mei:manifestation"/>
      </mei:manifestationList>
    </mei:fileDesc>
  </xsl:template>
</xsl:stylesheet>
